#!/usr/bin/env bash
# Runs ON the server. Usage: bash remote-deploy.sh /path/to/repo [branch]
#
# Deploys the branch the server checkout is on (or [branch], which must match it).
# Two run modes, auto-detected (override with DEPLOY_MODE=systemd|compose):
#   systemd  containers are started by a systemd unit ($SERVICE, default contentflow-bot)
#            with `docker run`; the app code is baked into the images, so images are
#            rebuilt from the checkout and the unit is restarted. The nginx "web"
#            container (contentflow-web), if present, is synced with the new build.
#   compose  containers are managed by docker compose in <repo>/contentflow.
#
# Where the code comes from: the git remote $DEPLOY_REMOTE (default origin) or, when the
# checkout has no such remote, the URL in $DEPLOY_REPO_URL. With DEPLOY_LOCAL=1 nothing is
# fetched: the committed local HEAD is deployed as it is.
#
# Safe by design: refuses to touch a checkout that has diverged or has uncommitted
# edits, backs up the database first, builds every image before replacing any, verifies
# the API, the web container and (optionally) the public URL afterwards, and restores
# the previous code, images and web files if anything fails. (The database itself is
# not rolled back; use the backup.)
set -euo pipefail

REPO_DIR="${1:?usage: remote-deploy.sh /path/to/repo [branch]}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000}"
WEB_URL="${WEB_URL:-http://127.0.0.1:3000}"
PUBLIC_URL="${PUBLIC_URL:-}"          # e.g. https://parsr.benderhost.org/app/ ; empty = skip
BACKUP_DIR="${BACKUP_DIR:-$HOME/contentflow-backups}"
KEEP_BACKUPS="${KEEP_BACKUPS:-14}"
HEALTH_TRIES="${HEALTH_TRIES:-30}"
HEALTH_DELAY="${HEALTH_DELAY:-2}"
SERVICE="${SERVICE:-contentflow-bot}"
DEPLOY_MODE="${DEPLOY_MODE:-auto}"
DB_CONTAINER="${DB_CONTAINER:-contentflow-db}"
WEB_CONTAINER="${WEB_CONTAINER:-contentflow-web}"
REMOTE_NAME="${DEPLOY_REMOTE:-origin}"
REPO_URL="${DEPLOY_REPO_URL:-}"
STAMP="$(date +%Y%m%d-%H%M%S)"

fail() { echo "::error::$*" >&2; exit 1; }

cd "$REPO_DIR"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "$REPO_DIR is not a git checkout"

CURRENT="$(git branch --show-current)"
[ -n "$CURRENT" ] || fail "server checkout is in detached HEAD state"
BRANCH="${2:-$CURRENT}"
[ "$CURRENT" = "$BRANCH" ] \
  || fail "server is on '$CURRENT', not '$BRANCH'; switch or merge it first"

[ -z "$(git status --porcelain --untracked-files=no)" ] \
  || fail "server has uncommitted changes; commit or stash them first"

if [ "$DEPLOY_MODE" = auto ]; then
  if command -v systemctl >/dev/null 2>&1 && systemctl cat "$SERVICE" >/dev/null 2>&1; then
    DEPLOY_MODE=systemd
  else
    DEPLOY_MODE=compose
  fi
fi
case "$DEPLOY_MODE" in systemd|compose) ;; *) fail "unknown DEPLOY_MODE '$DEPLOY_MODE'";; esac
echo "Mode: $DEPLOY_MODE, branch: $BRANCH"

PREV="$(git rev-parse HEAD)"
if [ "${DEPLOY_LOCAL:-0}" = 1 ]; then
  # Deploy exactly what is committed in this checkout, without touching the network.
  # The clean-tree and branch checks above still apply.
  echo "DEPLOY_LOCAL=1: deploying the local commit $PREV (no fetch)"
elif git remote get-url "$REMOTE_NAME" >/dev/null 2>&1; then
  git fetch "$REMOTE_NAME" "$BRANCH"
  UPSTREAM="$REMOTE_NAME/$BRANCH"
elif [ -n "$REPO_URL" ]; then
  git fetch "$REPO_URL" "$BRANCH"
  UPSTREAM="FETCH_HEAD"
else
  fail "no git remote '$REMOTE_NAME' in this checkout; set DEPLOY_REPO_URL or add the remote"
fi
if [ "${DEPLOY_LOCAL:-0}" != 1 ]; then
  git merge --ff-only "$UPSTREAM" \
    || fail "server branch has commits that are not upstream; push and merge them first (or set DEPLOY_LOCAL=1 to deploy the local commit)"
fi
echo "Deploying $PREV -> $(git rev-parse HEAD)"

SWAP_IMAGES=()
SWAPPED=0
RESTARTED=0
WEB_SYNCED=0
WEB_BACKUP_DIR=""

restart_services() {
  if [ "$DEPLOY_MODE" = systemd ]; then
    systemctl restart "$SERVICE"
  else
    (cd "$REPO_DIR/contentflow" && docker compose build && docker compose up -d --remove-orphans)
  fi
}

restore_web() {
  [ -n "$WEB_BACKUP_DIR" ] || return 0
  docker cp "$WEB_BACKUP_DIR/html/." "$WEB_CONTAINER:/usr/share/nginx/html/" || true
  docker cp "$WEB_BACKUP_DIR/default.conf" "$WEB_CONTAINER:/etc/nginx/conf.d/default.conf" || true
  docker exec "$WEB_CONTAINER" nginx -s reload || true
}

restore() {
  cd "$REPO_DIR"
  git reset --keep "$PREV" || echo "WARNING: could not reset the code to $PREV" >&2
  if [ "$SWAPPED" = 1 ]; then
    for img in "${SWAP_IMAGES[@]}"; do docker tag "$img-rollback" "$img" || true; done
  fi
  if [ "$RESTARTED" = 1 ]; then restart_services || echo "WARNING: restart after restore failed" >&2; fi
  if [ "$WEB_SYNCED" = 1 ]; then restore_web; fi
  echo "Restored $PREV. The database is unchanged by the restore; backup: ${BACKUP:-none}" >&2
}

on_exit() {
  local rc=$?
  [ "$rc" -eq 0 ] && return 0
  echo "::error::deploy failed (exit $rc); restoring the previous version" >&2
  restore
  exit "$rc"
}
trap on_exit EXIT

cd "$REPO_DIR/contentflow"

db_dump() {
  local dump='pg_dump -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-${POSTGRES_USER:-postgres}}"'
  if [ "$DEPLOY_MODE" = systemd ]; then
    docker exec "$DB_CONTAINER" sh -c "$dump"
  else
    docker compose exec -T postgres sh -c "$dump"
  fi
}

mkdir -p "$BACKUP_DIR"
BACKUP="$BACKUP_DIR/db-$STAMP.sql.gz"
db_dump | gzip > "$BACKUP"
[ "$(gzip -dc "$BACKUP" | wc -c)" -gt 0 ] || fail "database backup is empty, aborting before any change"
echo "Database backup: $BACKUP"
ls -1t "$BACKUP_DIR"/db-*.sql.gz | tail -n +"$((KEEP_BACKUPS + 1))" | xargs -r rm --

if [ "$DEPLOY_MODE" = systemd ]; then
  # Build every image under a temporary tag first, so a failed build changes nothing.
  for svc in api bot worker scheduler; do
    if ! img="$(docker inspect -f '{{.Config.Image}}' "contentflow-$svc" 2>/dev/null)"; then
      echo "Skipping $svc: no container named contentflow-$svc"
      continue
    fi
    echo "Building $img from docker/Dockerfile.$svc"
    docker build -f "docker/Dockerfile.$svc" -t "$img-candidate" .
    SWAP_IMAGES+=("$img")
  done
  [ "${#SWAP_IMAGES[@]}" -gt 0 ] || fail "no contentflow containers found to rebuild"

  SWAPPED=1
  for img in "${SWAP_IMAGES[@]}"; do
    docker tag "$img" "$img-rollback"
    docker tag "$img-candidate" "$img"
  done
fi

RESTARTED=1
restart_services

HAS_WEB=0
if [ "$DEPLOY_MODE" = systemd ] && docker inspect "$WEB_CONTAINER" >/dev/null 2>&1; then
  HAS_WEB=1
fi

# The nginx web container is not part of the unit and has no baked-in release, so it is
# updated in place: new build (taken from the freshly built API image) and nginx.conf.
sync_web() {
  WEB_BACKUP_DIR="$BACKUP_DIR/web-$STAMP"
  mkdir -p "$WEB_BACKUP_DIR"
  docker cp "$WEB_CONTAINER:/usr/share/nginx/html" "$WEB_BACKUP_DIR/html"
  docker cp "$WEB_CONTAINER:/etc/nginx/conf.d/default.conf" "$WEB_BACKUP_DIR/default.conf"
  WEB_SYNCED=1
  local tmp; tmp="$(mktemp -d)"
  docker cp contentflow-api:/app/web/build/. "$tmp"
  [ -f "$tmp/index.html" ] || fail "the API image has no web build; refusing to sync the web container"
  docker cp "$tmp/." "$WEB_CONTAINER:/usr/share/nginx/html/"
  rm -rf "$tmp"
  docker cp "$REPO_DIR/contentflow/web/nginx.conf" "$WEB_CONTAINER:/etc/nginx/conf.d/default.conf"
  docker exec "$WEB_CONTAINER" nginx -t
  docker exec "$WEB_CONTAINER" nginx -s reload
}

if [ "$HAS_WEB" = 1 ]; then
  sync_web
else
  echo "No $WEB_CONTAINER container: skipping web sync"
fi

bundle_of() { { curl -fsS -m 5 "$1" || true; } | grep -o 'main\.[a-z0-9]*\.js' | head -1 || true; }

healthy() {
  curl -fsS -m 5 "$HEALTH_URL/health" >/dev/null || return 1
  local page
  page="$(curl -fsS -m 5 "$HEALTH_URL/app/")" || return 1
  grep -q 'id="root"' <<<"$page" || return 1
  # Every place that serves the web app must serve the bundle the API just shipped.
  local want got
  want="$(bundle_of "$HEALTH_URL/app/")"
  [ -n "$want" ] || return 1
  if [ "$HAS_WEB" = 1 ]; then
    got="$(bundle_of "$WEB_URL/")"
    [ "$got" = "$want" ] || { echo "web container serves '$got', expected '$want'" >&2; return 1; }
  fi
  if [ -n "$PUBLIC_URL" ]; then
    got="$(bundle_of "$PUBLIC_URL")"
    [ "$got" = "$want" ] || { echo "$PUBLIC_URL serves '$got', expected '$want'" >&2; return 1; }
  fi
}

for _ in $(seq 1 "$HEALTH_TRIES"); do
  if healthy; then
    echo "Deploy OK: API healthy; web app consistent everywhere it is served"
    exit 0
  fi
  sleep "$HEALTH_DELAY"
done

fail "health check failed after deploy"

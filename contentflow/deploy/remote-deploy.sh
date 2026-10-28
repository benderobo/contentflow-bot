#!/usr/bin/env bash
# Runs ON the server. Usage: bash remote-deploy.sh /path/to/repo [branch]
#
# Deploys the branch the server checkout is on (or [branch], which must match it).
# Two run modes, auto-detected (override with DEPLOY_MODE=systemd|compose):
#   systemd  containers are started by a systemd unit ($SERVICE, default contentflow-bot)
#            with `docker run`; the app code is baked into the images, so images are
#            rebuilt from the checkout and the unit is restarted.
#   compose  containers are managed by docker compose in <repo>/contentflow.
#
# Safe by design: refuses to touch a checkout that has diverged from origin or has
# uncommitted edits, backs up the database first, builds every image before replacing
# any, verifies the API and the web app afterwards, and restores the previous code and
# images if anything fails. (The database itself is not rolled back; use the backup.)
set -euo pipefail

REPO_DIR="${1:?usage: remote-deploy.sh /path/to/repo [branch]}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/contentflow-backups}"
KEEP_BACKUPS="${KEEP_BACKUPS:-14}"
HEALTH_TRIES="${HEALTH_TRIES:-30}"
HEALTH_DELAY="${HEALTH_DELAY:-2}"
SERVICE="${SERVICE:-contentflow-bot}"
DEPLOY_MODE="${DEPLOY_MODE:-auto}"
DB_CONTAINER="${DB_CONTAINER:-contentflow-db}"

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
git fetch origin "$BRANCH"
git merge --ff-only "origin/$BRANCH" \
  || fail "server branch has commits that are not in origin/$BRANCH; push and merge them first"
echo "Deploying $PREV -> $(git rev-parse HEAD)"

SWAP_IMAGES=()
SWAPPED=0
RESTARTED=0

restart_services() {
  if [ "$DEPLOY_MODE" = systemd ]; then
    systemctl restart "$SERVICE"
  else
    (cd "$REPO_DIR/contentflow" && docker compose build && docker compose up -d --remove-orphans)
  fi
}

restore() {
  cd "$REPO_DIR"
  git reset --keep "$PREV" || echo "WARNING: could not reset the code to $PREV" >&2
  if [ "$SWAPPED" = 1 ]; then
    for img in "${SWAP_IMAGES[@]}"; do docker tag "$img-rollback" "$img" || true; done
  fi
  if [ "$RESTARTED" = 1 ]; then restart_services || echo "WARNING: restart after restore failed" >&2; fi
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
BACKUP="$BACKUP_DIR/db-$(date +%Y%m%d-%H%M%S).sql.gz"
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

healthy() {
  curl -fsS -m 5 "$HEALTH_URL/health" >/dev/null || return 1
  local page
  page="$(curl -fsS -m 5 "$HEALTH_URL/app/")" || return 1
  grep -q 'id="root"' <<<"$page"
}

for _ in $(seq 1 "$HEALTH_TRIES"); do
  if healthy; then
    echo "Deploy OK: API healthy and web app served at /app/"
    exit 0
  fi
  sleep "$HEALTH_DELAY"
done

fail "health check failed after deploy"

#!/usr/bin/env bash
# Runs ON the server. Usage: bash remote-deploy.sh /path/to/repo [branch]
#
# Safe by design: it refuses to touch a server whose checkout has diverged from
# origin or has uncommitted edits, backs up the database first, verifies the API
# and the web app after the rebuild, and rolls the code back if the check fails.
# (A rollback restores the code only; restore the DB from the backup if needed.)
set -euo pipefail

REPO_DIR="${1:?usage: remote-deploy.sh /path/to/repo [branch]}"
BRANCH="${2:-main}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8000}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/contentflow-backups}"
KEEP_BACKUPS="${KEEP_BACKUPS:-14}"
HEALTH_TRIES="${HEALTH_TRIES:-30}"
HEALTH_DELAY="${HEALTH_DELAY:-2}"

fail() { echo "::error::$*" >&2; exit 1; }

cd "$REPO_DIR"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "$REPO_DIR is not a git checkout"

[ "$(git branch --show-current)" = "$BRANCH" ] \
  || fail "server is on '$(git branch --show-current)', not '$BRANCH'; merge it into $BRANCH first"

[ -z "$(git status --porcelain --untracked-files=no)" ] \
  || fail "server has uncommitted changes; commit or stash them first"

PREV="$(git rev-parse HEAD)"
git fetch origin "$BRANCH"
git merge --ff-only "origin/$BRANCH" \
  || fail "server branch has commits that are not in origin/$BRANCH; push and merge them first"
NEW="$(git rev-parse HEAD)"
echo "Deploying $PREV -> $NEW"

cd contentflow

mkdir -p "$BACKUP_DIR"
BACKUP="$BACKUP_DIR/db-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$BACKUP"
[ "$(gzip -dc "$BACKUP" | wc -c)" -gt 0 ] || fail "database backup is empty, aborting before any change"
echo "Database backup: $BACKUP"
ls -1t "$BACKUP_DIR"/db-*.sql.gz | tail -n +"$((KEEP_BACKUPS + 1))" | xargs -r rm --

docker compose build
docker compose up -d --remove-orphans

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

echo "::error::health check failed after deploy; rolling back code to $PREV" >&2
cd "$REPO_DIR"
git reset --keep "$PREV"
cd contentflow
docker compose build
docker compose up -d --remove-orphans
echo "Rolled back to $PREV. Database backup kept at $BACKUP" >&2
exit 1

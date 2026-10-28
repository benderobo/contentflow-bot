#!/usr/bin/env bash
# Run ON the server as root:
#   bash install-gate.sh /path/to/repo "ssh-ed25519 AAAA... comment" ["ssh-ed25519 AAAA... other"]
# Creates the unprivileged user "cfdeploy" whose only way in is a key that can run
# `status`, `logs <svc> [n]` and `deploy` (see cf-ssh-gate). Idempotent; re-run to change keys.
# Remove: userdel -r cfdeploy; rm -rf /etc/sudoers.d/cfdeploy /usr/local/bin/cf-ssh-{entry,gate} /usr/local/lib/contentflow
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "run as root" >&2; exit 1; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${1:?usage: install-gate.sh /path/to/repo \"ssh-ed25519 AAAA...\" [more keys]}"; shift
[ "$#" -ge 1 ] || { echo "give at least one public key" >&2; exit 1; }
[ -d "$REPO_DIR/.git" ] || [ -f "$REPO_DIR/.git" ] || { echo "$REPO_DIR is not a git checkout" >&2; exit 1; }
for k in "$@"; do
  [[ "$k" =~ ^ssh-ed25519\ AAAA[0-9A-Za-z+/=]+(\ [^\"\'\;\&\|\`\$]*)?$ ]] \
    || { echo "not a plain ssh-ed25519 public key: ${k:0:40}..." >&2; exit 1; }
done
USER_NAME="${CF_USER:-cfdeploy}"
BIN="${CF_BIN:-/usr/local/bin}"
CONF="${CF_CONF:-/etc/contentflow-deploy.env}"

id "$USER_NAME" >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash "$USER_NAME"
# '*' (not '!'): no password can ever match, but sshd does not treat the account as locked
usermod -p '*' "$USER_NAME"
LIB="${CF_LIB:-/usr/local/lib/contentflow}"
install -d -o root -g root -m 0755 "$LIB"
install -o root -g root -m 0755 "$HERE/../remote-deploy.sh" "$LIB/remote-deploy.sh"
install -o root -g root -m 0755 "$HERE/cf-ssh-entry" "$BIN/cf-ssh-entry"
install -o root -g root -m 0755 "$HERE/cf-ssh-gate"  "$BIN/cf-ssh-gate"

if [ ! -e "$CONF" ]; then
  cat > "$CONF" <<CONFEOF
# Read by cf-ssh-gate (and passed to remote-deploy.sh). No secrets here.
REPO_DIR=$REPO_DIR
# PUBLIC_URL=https://parsr.benderhost.org/app/
# DEPLOY_REPO_URL=https://github.com/benderobo/contentflow-bot.git
# DEPLOY_LOCAL=1   # deploy the committed local HEAD without fetching (no origin / unpushed commits)
CONFEOF
  chmod 0644 "$CONF"
fi

tmp="$(mktemp)"
echo "$USER_NAME ALL=(root) NOPASSWD: $BIN/cf-ssh-gate" > "$tmp"
if command -v visudo >/dev/null 2>&1; then visudo -cf "$tmp" >/dev/null || { echo "sudoers check failed" >&2; exit 1; }; fi
install -o root -g root -m 0440 "$tmp" "/etc/sudoers.d/$USER_NAME"; rm -f "$tmp"

home="$(getent passwd "$USER_NAME" | cut -d: -f6)"
install -d -o "$USER_NAME" -g "$USER_NAME" -m 0700 "$home/.ssh"
: > "$home/.ssh/authorized_keys"
for k in "$@"; do
  echo "restrict,command=\"$BIN/cf-ssh-entry\" $k" >> "$home/.ssh/authorized_keys"
done
chown "$USER_NAME:$USER_NAME" "$home/.ssh/authorized_keys"; chmod 0600 "$home/.ssh/authorized_keys"

echo "Installed. User: $USER_NAME   Repo: $REPO_DIR   Config: $CONF"
echo "Allowed over SSH: status | logs <api|bot|worker|scheduler|web|db> [lines] | deploy"
echo "Try from the client:  ssh $USER_NAME@<host> status"

# ContentFlow deploy

## How the system is built and served

| Piece | Built from | Runs as | Notes |
|---|---|---|---|
| API | `docker/Dockerfile.api` (node stage builds `web/`, python stage bakes code + `web/build`) | `contentflow-api`, `:8000` | serves `/api/*` and the web app at `/app/` |
| bot, worker, scheduler | `docker/Dockerfile.{bot,worker,scheduler}` | `contentflow-bot/-worker/-scheduler` | code is **baked into the image** (`COPY . .`, run from `/app`) |
| web | `web/Dockerfile` (nginx + build) | `contentflow-web`, `:3000` | what the public domain may serve; proxies `/api/` to the API |
| db / cache | `postgres:16-alpine`, `redis:7-alpine` | `contentflow-db`, `contentflow-cache` | data lives in docker volumes |

Production starts these with `docker run` from a systemd unit (`contentflow-bot`,
`/usr/local/bin/contentflow-start.sh`), not with docker compose. The `-v <repo>/contentflow:/app/contentflow`
mount in that script does **not** update running code: the apps run from the baked copy in `/app`.
A `git pull` + restart changes nothing; images must be rebuilt.

## Deploy

`remote-deploy.sh <repo root> [branch]` (on the server) does it all: backup the DB, build the
images under candidate tags, swap, restart the unit, sync the nginx `web` container with the
new build and `nginx.conf`, verify that the API, the web container and (optionally) `PUBLIC_URL`
all serve the same bundle, and restore code, images and web files if anything fails.
Without an `origin` remote set `DEPLOY_REPO_URL`. Tested by simulation (69 checks).

## SSH access with least privilege (`ssh-gate/`)

`install-gate.sh` creates the user `cfdeploy`; its key can only run, via a forced command:

    status                      containers, image ages, health, which bundle each place serves
    logs <api|bot|worker|scheduler|web|db> [lines]
    deploy                      one at a time (lock), exit code is passed through

No shell, no pty, no forwarding, no sftp. Every request is logged to the journal
(`journalctl -t cf-ssh-entry`). Config: `/etc/contentflow-deploy.env` (`REPO_DIR`, optional
`PUBLIC_URL`, `DEPLOY_REPO_URL`). Remove: `userdel -r cfdeploy; rm -rf /etc/sudoers.d/cfdeploy
/usr/local/bin/cf-ssh-{entry,gate} /usr/local/lib/contentflow`.

`deploy-contentflow.workflow.yml` is a manual GitHub Actions workflow that calls `deploy`
through this key (copy it to `.github/workflows/`).

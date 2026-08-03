---
name: insite-studio-stack
description: "IN_SITE Studio stack on host r1116005 (/root) — how the AI agents build client sites, ports, paths, and the /build + Telegram control added 2026-06-02"
metadata: 
  node_type: memory
  type: project
  originSessionId: 038bc754-8e0c-4c95-bf0b-2ddcca770460
---

IN_SITE Studio ("E-T-E LABORATORY") lives on the host whose cwd is `/root` (hostname r1116005), reachable at `https://bendernostur.duckdns.org:88/insite/`. This is a SEPARATE host from the older `/home/bender` Parrot workstation and from "host b" in older memory — though Telegram getWebhookInfo resolves the domain to `167.17.180.42`.

**Architecture (port :88 nginx site = `/etc/nginx/sites-available/n8n`):**
- `/var/www/insite/` static: `index.html` (client form), `admin.html` (manager inbox, basic-auth), `studio.html` (AI Studio chat, basic-auth). htpasswd: `/etc/nginx/.htpasswd_insite`.
- `/insite/api/` → `127.0.0.1:9123` = Python `insite-api.service` (`/home/insite-api/server.py`, runs as root). Orders stored in `/home/insite-api/orders.json`. Auth: basic `root:S1h2i3s4h5@!`; POST /orders uses header `X-INSITE-KEY: insite-secret-2026`.
- `/` and `/webhook/...` → `127.0.0.1:5678` = n8n (docker container `n8n`, v2.17.8, DB volume `/var/lib/docker/volumes/n8n_n8n_data/_data/database.sqlite`, encryptionKey in `/home/node/.n8n/config`).

**The "agents" = n8n Code nodes calling Google Gemini** (`gemini-2.5-flash`, key `$env.GOOGLE_AI_API_KEY`). Workflows: `IN_SITE Task Router` (webhook `insite/task`, dept→Gemini→text) and `IN_SITE Creative Manager` (webhook `insite/project`, breaks project into tasks → fans out to task router). They only returned TEXT.

**Original problem "агенты не делают сайт":** agents produced text/plans only — nothing wrote/deployed real HTML. Also `notify_manager` had a 15s urlopen timeout (Gemini takes ~11-34s) so orders lost `agent_notes`, and the task-router node capped `maxOutputTokens:2000` (too small for a full page).

**Fix added 2026-06-02 (see [[insite-site-builder-and-bot]] for the build details):**
1. `insite-api` `POST /build` (basic-auth): brief→Gemini (8192 tokens, strict "only HTML" prompt)→extract `<!DOCTYPE..</html>`→write `/var/www/insite/sites/<order_id>/index.html`→returns `https://bendernostur.duckdns.org:88/insite/sites/<id>/` and patches order `site_url`+`status:built`. Gemini key passed via systemd drop-in `/etc/systemd/system/insite-api.service.d/env.conf`. Timeout bumped 15→60s.
2. admin.html: "🏗 Собрать сайт" button per order.
3. Telegram @benderobo_bot (token owned by n8n workflow `claude-bot-001` "Claude Telegram Bot", credential `tg-cred-001`, decrypted via encryptionKey for env passthrough): extended the "Claude Handler" Code node with `/insite`, `/orders`, `/build <id>`, `/agent <dept> | <task>`. Backup of original workflow in `/root/backups/n8n/`.
4. New-order push: `insite-api` `tg_notify_order()` sends a Telegram alert on each new POST /orders to the chat id in `/home/insite-api/admin_chat.txt`. Bot token passed to insite-api via the same systemd drop-in (`TELEGRAM_BOT_TOKEN`). `POST /admin_chat` (basic auth) writes that file.
5. Admin lock: bot is restricted to one owner. Command `/notify_here <admin-pass>` (pass = `S1h2i3s4h5@!`) stores `sd.adminChatId` in n8n static data, registers the push chat, and locks the bot — any chat != adminChatId gets a silent `return []`. Until claimed the bot stays open, so the owner must run `/notify_here <pass>` once.

Deploy method for the bot: `docker stop n8n` → python sqlite update of `workflow_entity.nodes` for claude-bot-001 → `docker start n8n` (syntax-check jsCode first by wrapping in `async function`). The bot runs on a Telegram webhook, not polling.

**Verified/added 2026-06-02 (session 2):**
- n8n container is managed by **docker-compose v1** (`/usr/bin/docker-compose`, NOT `docker compose` v2 — that errors). Compose file: `/home/n8n/docker-compose.yml` (service `n8n`, `depends_on: renderer` built from `/home/renderer`). All secrets + env live in that compose `environment:` block, e.g. `TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL=openrouter/free`, `GOOGLE_AI_API_KEY`, `TELEGRAM_ALLOWED_CHAT_ID`, `TELEGRAM_ALLOWED_THREAD_ID`, `TELEGRAM_TEST_CHAT_ID`. To apply env changes: `cd /home/n8n && docker-compose up -d n8n` (recreates container; all 6 workflows auto-reactivate, webhook re-registers).
- The bot's general chat + `/gen` use **OpenRouter** (`openrouter/free`); only the IN_SITE agents (task router / creative manager) use Gemini. So the bot mixes two providers.
- @benderobo_bot = id `8642525554`. Telegram webhook (healthy, pending 0): `https://bendernostur.duckdns.org:88/webhook/claude-tg-bot/webhook` (webhookId `claude-tg-bot`). Allowed group `TELEGRAM_ALLOWED_CHAT_ID=-1003048324752` is the supergroup **`#Pyt🛝con`** (a forum/topic group → bot only answers in thread `TELEGRAM_ALLOWED_THREAD_ID=2375`; messages in other threads hit a silent `return []` before any command logic, so /notify_here must be sent in a PRIVATE chat or in thread 2375).
- `admin_chat.txt` was created `= -1003048324752` (group #Pyt🛝con), so new-order push now targets that group. This is independent of the bot lock.
- Bot lock NOT yet active as of 2026-06-02: `global.adminChatId` is still None (/notify_here never run). NOTE the staticData shape is `{"global":{"users":{...},"adminChatId":...}}` — read `global.adminChatId`, not the top level (7 users with history were tracked, so staticData DOES persist fine).
- Silenced recurring `SQLITE_CONSTRAINT: FOREIGN KEY constraint failed` log spam by adding `N8N_DISABLED_MODULES=insights` to the compose env. Root cause was n8n's background "insights" compaction/pruning (tables `insights_metadata/raw/by_period`), NOT data corruption — `PRAGMA foreign_key_check` is clean and it never affected staticData, orders, or the bot. Side effect: the Insights dashboard in the n8n UI is now empty. Revert by removing that env line + `docker-compose up -d n8n`.

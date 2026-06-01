## User Profile

The user works mainly on a Linux desktop under `/home/bender`, but a large share of their useful context lives in local repos, local rule files, and a few recurring remote systems. The main repeated areas are `/home/bender/cloude_proj` with live bot/VPN operations, `/home/bender/vpn-gateway` for upgrade planning and secret-safe docs, `/home/bender/ARGUS` for practical repo usage, and host-level maintenance on the Parrot workstation itself.

They usually want practical execution, not long theory. Good runs act on the real target, verify with logs/status/artifacts, and make boundaries explicit when the blocker is environment, privilege, or live-state uncertainty. They also care about not repeating mistakes: confirm the real host/path first, check the actual code/data flow before editing, and preserve already-working behavior while fixing the broken path.

Russian is a stable preference in many local-maintenance sessions. The user often gives short steering corrections such as `проверяй`, `каталог purple`, `так расскажи ... сжато но понятно`, or `как успехи`, so future agents should react quickly, keep scope tight, and avoid forcing generic solutions when the setup looks mismatched.

## User preferences

- When a fix may delete files, modify global config, or change the installation, briefly explain what the fix will do first, then ask for confirmation.
- Safe read-only checks are allowed without asking first.
- If a suggested fix looks wrong for the user’s setup, say so and stop instead of forcing a generic repair.
- If the user repeats `отвечай на русском` or switches with `пиши на русском`, continue in Russian for the rest of the session.
- When the user asks to scan local directories for memory, treat it literally as a filesystem-memory task, not a conceptual discussion.
- For setup requests like `инструкция как запустить venv ... с пояснениями`, give end-to-end practical steps with brief explanations.
- For requests like `сжато но понятно` about a large tool catalog, keep full coverage but compress it into a sectioned overview.
- When the user asks for a structured system report "с пояснениями", summarize what the findings mean instead of dumping raw command output.
- If the user says `да продолжи` after a diagnosis, continue into the next practical remediation step without making them restate the task.
- For hardware capability requests such as monitor mode, verify chipset/driver support before promising the feature.
- When system tuning or risky host maintenance is requested, inspect/simulate first, then apply only clearly safe changes.
- Keep root-only or privileged actions separate and visible; if the user must run one manually, present one clean line and warn about line wrapping.
- For interactive maintenance scripts, do not auto-answer prompts. The user explicitly said `хочу отвечать сам`.
- For desktop/system-tuning helpers on this host, prefer Russian explanations, especially for services and autostarts.
- Reversible `status/apply/rollback` workflows are a strong default for local optimization and KDE-tuning tasks.
- If a target name is ambiguous, expect terse clarifications like `каталог purple` and narrow to the local path quickly.
- If a requested package/app name is ambiguous, ask one quick clarification before installing; `install bitwise` turned out to mean `Bitvise SSH Client`.
- On remote host `b` work, verify each material change with logs, service state, `docker-compose`, `curl`, or output artifacts.
- If a live remote task has multiple known hosts, confirm the exact machine first; `b` and `Amnezia` are different targets.
- When the user points to docs/rule files or says `проверяй логику кода перед исправлением`, build the real execution path first before editing.
- Preserve intended bot role splits and working behaviors while fixing broken paths; do not make one bot work by silently breaking the other.
- If the user says `неработает` or `инста не работает`, stop proposing more variants and verify the exact client/use path end to end.
- If the user asks to save upgrade work under `#upgrade_vpn` or "создай файл памяти", keep a dedicated working memory file instead of relying only on chat history.
- For public/private documentation splits, keep public docs redacted and move live credentials, restore files, and panel URLs into `private/`-style storage.

## General Tips

- `rg` is not installed in this environment. Start with `grep -RIn`, `find`, `type -a`, and targeted `sed`.
- On this host, interactive `sudo` is a recurring boundary. Say clearly when verification or remediation is blocked by password prompts.
- For `/home/bender/.claude/settings.json` or similar home-config issues, do a read-only inspection first, summarize the likely edit, and ask before writing.
- On this Btrfs host, `swapon failed: Invalid argument` plus `filefrag -v /swapfile` showing extents is a strong signal to recreate the file with `btrfs filesystem mkswapfile`.
- `NetworkManager` dispatcher hooks under `/etc/NetworkManager/dispatcher.d` are a viable pattern for Wi-Fi-startup automation on this machine.
- Separate repo-local failures from host/environment blockers. `/home/bender/purple` was limited by `/etc/ssh` ownership and crates.io reachability, not obvious repo breakage.
- For shell-behavior bugs, use interactive resolution checks like `bash -ic 'type -a <cmd>; alias <cmd> 2>/dev/null || true'`.
- `journalctl` is high-value for reconstructing past disk-copy, swap, and service-failure history on this machine.
- For webcam diagnostics here, `ffmpeg -f v4l2 -list_formats all -i /dev/video0` plus a one-frame capture is a fast truth test.
- For Bitvise-on-Linux attempts on this host, check Wine architecture support early; `wine64` alone was not enough.
- On remote host `b`, the real n8n workflow DB is `/var/lib/docker/volumes/n8n_n8n_data/_data/database.sqlite`; inspect execution tables before guessing which workflow/node failed.
- In this n8n stack, `fetch is not defined` means the runner expects `this.helpers.httpRequest`, and file-output issues often require checking both `N8N_RESTRICT_FILE_ACCESS_TO` and `/output` ownership.
- For the `Amnezia` VPN host, a real Xray client test plus a real Instagram request is the fastest truth test for backend transport viability.

## What's in Memory

### /home/bender

#### 2026-05-08

- Local memory scanning requests and Russian-default routing: отвечай на русском, просканируй локальные директории на наличие памяти, memory artifacts, filesystem scan
  - desc: Routing note for memory-maintenance tasks from `cwd=/home/bender`. Search this first when the user explicitly asks to scan local directories for memory artifacts or repeats the Russian-language requirement.
  - learnings: only the request wording is validated here; do not assume a scan already succeeded without fresh tool output.

#### 2026-05-07

- Home-directory Claude config fixes with confirmation gate: /home/bender/.claude/settings.json, Invalid or malformed JSON, global config, read-only checks
  - desc: Covers cautious repairs for Claude/home-directory config problems on `cwd=/home/bender`, especially when edits may touch global config or installation state.
  - learnings: read-only inspection is allowed without asking, but any config-changing or destructive command needs a brief explanation first and explicit confirmation.

- Parrot workstation audit, Wi-Fi DNS automation, and Btrfs swap repair: system_audit_report_2026-05-07.md, install_wifi_dns.sh, btrfs filesystem mkswapfile, swapfile.swap, monitor mode
  - desc: Runbook for host inventory, Wi-Fi startup DNS automation, and fixing `swapfile.swap` on this Parrot/Btrfs machine. Includes follow-up context for monitor-mode-capable USB Wi-Fi adapters. Applies to `cwd=/home/bender`.
  - learnings: `NetworkManager` dispatcher hooks are viable here; `swapon failed: Invalid argument` plus `filefrag` extents on `/swapfile` means recreate it with `btrfs filesystem mkswapfile`.

### /home/bender/ARGUS

#### 2026-05-07

- ARGUS venv activation and concise full-menu overview: /home/bender/ARGUS/venv, source venv/bin/activate, argus.py, README.md, OSINT, Stress Testing
  - desc: Covers practical startup steps, dependency verification, and a compact Russian map of all ARGUS menu sections. Search this first for `/home/bender/ARGUS` setup or `расскажи про все пункты` requests.
  - learnings: the repo already has `venv`; `README.md` plus `argus.py` are the authoritative sources for both launch steps and menu coverage.

### /home/bender/vpn-gateway

#### 2026-05-06

- vpn-gateway upgrade planning, secret splitting, and DDNS/VPN access: upgrade_vpn_memory.md, upgrade-awg-bot-plan.md, private/access.md, stealthsurf, /json/{token}, /to/{token}, DuckDNS
  - desc: Planning/docs memory for `cwd=/home/bender` and `/home/bender/vpn-gateway`: subscription-format analysis, public/private doc boundaries, additive `awg-bot` upgrade planning, and offsite router-access guidance.
  - learnings: preserve both JSON and `vless://` subscription formats, keep live secrets under `private/`, and route offsite access through `DDNS -> VPN -> LAN router` instead of exposing admin directly.

### Older Memory Topics

#### /home/bender/cloude_proj

- Live VPN bot debugging and project archive on host `Amnezia`: Amnezia, 194.87.178.95, awg-bot.service, xray-xhttp443, Happ, V2Box, project_history_2026-05-02.tar.gz
  - desc: Distinguishes the live `Amnezia` VPN host from host `b`, covers real transport verification with Xray/Instagram tests, and documents the project-history archive flow to Desktop. Applies to `cwd=/home/bender/cloude_proj`.

- Host `b` bot split, n8n debugging, and media routing: /home/bot_tg, /home/comport_bot, /home/n8n, workflow_history, IMAGE_PROCESS_FAILED, TELEGRAM_TEST_CHAT_ID
  - desc: Full live bot/n8n memory for host `b`, including docs-first plan checks, token/webhook ownership, SQLite chat memory, `/genimg` activation, malformed PNG diagnosis, media fallback behavior, and `skills/remote-n8n-debug/SKILL.md`. Applies to `cwd=/home/bender/cloude_proj` plus the linked host `b` paths.

#### /home/bender

- Desktop system maintenance and KDE tuning: optimize_parrot.sh, aa-notify, conky, plasma-plasmashell.service, telegram-desktop
  - desc: Older host-maintenance runbook for safe optimization, KDE/Plasma recovery, reversible scripts, and Telegram install/recovery on `cwd=/home/bender`.

- Shell config and command wrappers: claude, .bashrc, claude-vpn, vpn-launch, bash -ic
  - desc: Search here when a command unexpectedly launches VPN or another wrapper; includes the alias chain and the verification method that proved `claude` resolves directly again. Applies to `cwd=/home/bender`.

- Bitvise SSH Client Wine install attempts: Bitvise SSH Client, bitwise, wine32:i386, syswow64, BvSshClient-Inst.exe
  - desc: Installing the Windows-only Bitvise client on this Parrot/Linux host, including ambiguity handling and the decisive missing-`wine32` blocker strings. Applies to `cwd=/home/bender`.

- Hardware setup and storage verification: FaceTime HD Camera, /dev/video0, ffmpeg -f v4l2, journalctl, fstab, @home
  - desc: End-to-end webcam verification plus evidence-based SSD clone/bootability checks. Applies to `cwd=/home/bender`.

- Keyboard configuration requests: F3, F4, MacBook, function keys
  - desc: Low-confidence routing note for the unverified request to make F3/F4 behave like on a MacBook; verify actual behavior before claiming it is configured. Applies to `cwd=/home/bender`.

#### /home/bender/purple

- `purple` repo validation and host blockers: /home/bender/purple, purple-ssh, ci.sh, cargo check --locked, static.crates.io, ssh -G
  - desc: Separates local Rust repo facts from host-level SSH permission and crates.io connectivity blockers. Applies to `cwd=/home/bender/purple`.

#### /home/bender/SLAM-LIVOX-HORIZON-EN

- Operator tooling, Pi 4 mode, and fork publishing: SLAM-LIVOX-HORIZON-EN, gpu обработчик pcb, webui, Raspberry Pi OS, SLAM_WIN_edition
  - desc: Covers the operator-facing web UI, GPU PCD tooling, Pi 4 safe mode, SD-image flow, and closed-fork publishing workflow for this checkout. Applies to `cwd=/home/bender/SLAM-LIVOX-HORIZON-EN`.

#!/usr/bin/env python3
"""
Sunny English — Lesson progress server
Per-student architecture: admin + multiple students can track progress independently
Students verified via invite code or admin password
Admin sees all students' progress, each student sees own
"""
import json, os, logging, threading, time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request

BOT_TOKEN = "8655259510:AAGd1iMvLL_ZZw77j2O8RXztspq94Xd2HtM"
ADMIN_CHAT_ID = "1139186144"
ADMIN_PASSWORD = "noinspiration"
DATA_FILE = "/root/sunnyenglish/lessons_progress.json"
STUDENTS_FILE = "/root/sunnyenglish/students.json"
INVITES_FILE = "/root/sunnyenglish/invites.json"
PORT = 8089

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("sunny-lessons")

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_progress():
    """Load progress with automatic migration from old flat format to per-student format"""
    data = load_json(DATA_FILE, {})
    if "done" in data and isinstance(data.get("done"), list):
        old_done = data.get("done", [])
        old_chat_id = data.get("chat_id", "")
        return {"milasha": {"done": old_done, "chat_id": old_chat_id}}
    return data if data else {"milasha": {"done": [], "chat_id": ""}}

def save_progress(data):
    save_json(DATA_FILE, data)

def load_students():
    return load_json(STUDENTS_FILE, {})

def save_students(data):
    save_json(STUDENTS_FILE, data)

def load_invites():
    return load_json(INVITES_FILE, {})

def save_invites(data):
    save_json(INVITES_FILE, data)

def generate_invite(child_name):
    import random, string
    code = child_name.upper()[:8] + "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    invites = load_invites()
    invites[code] = {"child": child_name, "created": time.time(), "active": True}
    save_invites(invites)
    return code

def verify_invite(code):
    invites = load_invites()
    code_upper = code.upper().strip()
    if code_upper in invites and invites[code_upper].get("active", False):
        return invites[code_upper]
    for k, v in invites.items():
        if k.upper() == code_upper and v.get("active", False):
            return v
    return None

def send_telegram(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.error(f"Telegram send error: {e}")

def forward_message(chat_id, text, user_name, user_id):
    admin_text = f"📩 <b>Сообщение от ученика</b>\n👤 {user_name} (ID: {user_id})\n\n{text}"
    kb = {"inline_keyboard": [[
        {"text": "✅ Урок 1", "callback_data": "close_1"},
        {"text": "✅ Урок 2", "callback_data": "close_2"},
        {"text": "✅ Урок 3", "callback_data": "close_3"}
    ], [
        {"text": "✅ Урок 4", "callback_data": "close_4"},
        {"text": "✅ Урок 5", "callback_data": "close_5"},
        {"text": "✅ Урок 6", "callback_data": "close_6"}
    ], [
        {"text": "✅ Урок 7", "callback_data": "close_7"},
        {"text": "✅ Урок 8", "callback_data": "close_8"},
        {"text": "✅ Урок 9", "callback_data": "close_9"}
    ], [
        {"text": "✅ Урок 10", "callback_data": "close_10"},
        {"text": "✅ Урок 11", "callback_data": "close_11"},
        {"text": "✅ Урок 12", "callback_data": "close_12"}
    ], [
        {"text": "✅ Урок 13", "callback_data": "close_13"},
        {"text": "✅ Урок 14", "callback_data": "close_14"},
        {"text": "✅ Урок 15", "callback_data": "close_15"}
    ], [
        {"text": "🔄 Сбросить всё", "callback_data": "reset_all"}
    ]]}
    send_telegram(ADMIN_CHAT_ID, admin_text, reply_markup=kb)

def handle_callback(query):
    data = query.get("data", "")
    user_id = str(query.get("from", {}).get("id", ""))
    msg = query.get("message", {})
    chat_id_raw = msg.get("chat", {}).get("id", "")
    chat_id = str(chat_id_raw) if chat_id_raw else ""

    log.info(f"Callback query: data={data}, user_id={user_id}, chat_id={chat_id}, admin_chat_id={ADMIN_CHAT_ID}")

    if chat_id != ADMIN_CHAT_ID:
        log.warning(f"Callback from non-admin chat: {chat_id} (expected {ADMIN_CHAT_ID})")
        return

    progress = load_progress()
    student = "milasha"

    if data.startswith("close_"):
        try:
            num = int(data.split("_")[1])
            if 1 <= num <= 15:
                if student not in progress:
                    progress[student] = {"done": [], "chat_id": chat_id}
                if num not in progress[student]["done"]:
                    progress[student]["done"].append(num)
                    save_progress(progress)
                    send_telegram(ADMIN_CHAT_ID, f"✅ Урок <b>{num}</b> закрыт для {student}! ({len(progress[student]['done'])}/15)")
                    log.info(f"Lesson {num} closed for {student} by admin (user_id={user_id})")
                else:
                    send_telegram(ADMIN_CHAT_ID, f"ℹ️ Урок <b>{num}</b> уже закрыт для {student}.")
        except (ValueError, IndexError) as e:
            log.error(f"Error parsing close callback: {data}, error: {e}")
    elif data == "reset_all":
        if student not in progress:
            progress[student] = {"done": [], "chat_id": chat_id}
        progress[student]["done"] = []
        save_progress(progress)
        send_telegram(ADMIN_CHAT_ID, f"🔄 Прогресс для {student} сброшен! Все уроки снова активны.")
        log.info(f"Progress reset for {student} by admin")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    req = urllib.request.Request(url, data=json.dumps({"callback_query_id": query["id"]}).encode(), headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        log.error(f"Error answering callback query: {e}")

def handle_message(msg):
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = (msg.get("text") or "").strip()
    user = msg.get("from", {}).get("first_name", "")
    user_id = str(msg.get("from", {}).get("id", ""))

    if not text:
        return

    is_admin = (chat_id == ADMIN_CHAT_ID)

    if is_admin:
        handle_admin_command(chat_id, text, user)
    else:
        handle_student_message(chat_id, text, user, user_id)

def handle_student_message(chat_id, text, user, user_id):
    students = load_students()
    students[user_id] = {"name": user, "chat_id": chat_id, "last_message": text}
    save_students(students)
    forward_message(chat_id, text, user, user_id)
    send_telegram(chat_id,
        f"👋 Привет, {user}! Твоё сообщение отправлено преподавателю.\n\n"
        "Жди ответа здесь! Если хочешь узнать свой прогресс — отправь /status"
    )
    log.info(f"Student message from {user} ({user_id}): {text}")

def handle_admin_command(chat_id, text, user):
    progress = load_progress()

    if text.lower() in ("/status", "статус"):
        msg_text = "📊 <b>Прогресс по студентам:</b>\n"
        for student, data in progress.items():
            if isinstance(data, dict) and "done" in data:
                done = data["done"]
                msg_text += f"\n👤 <b>{student}</b>: {len(done)}/15 уроков\n"
                for i in range(1, 16):
                    mark = "✅" if i in done else "⬜"
                    msg_text += mark
                msg_text += "\n"
        send_telegram(chat_id, msg_text)
        return

    if text.lower() in ("/reset", "сброс"):
        for student in progress:
            if isinstance(progress[student], dict) and "done" in progress[student]:
                progress[student]["done"] = []
        save_progress(progress)
        send_telegram(chat_id, "🔄 Весь прогресс по всем студентам сброшен!")
        log.info(f"All progress reset by {user}")
        return

    if text.lower().startswith("/invite"):
        parts = text.split(maxsplit=1)
        if len(parts) >= 2:
            child_name = parts[1].strip()
            code = generate_invite(child_name)
            send_telegram(chat_id, f"🔑 <b>Инвайт-код создан!</b>\n\nРебёнок: {child_name}")
            send_telegram(chat_id, f"<code>{code}</code>")
            send_telegram(chat_id, f"Ссылка: https://sunnyenglish.benderhost.org/courseplan?code={code}")
            log.info(f"Invite created for {child_name}: {code}")
        else:
            send_telegram(chat_id, "⚠️ Формат: /invite <b>имя_ребёнка</b>")
        return

    if text.lower().startswith("/close"):
        parts = text.split()
        if len(parts) >= 2:
            try:
                num = int(parts[1])
                student = "milasha"
                if 1 <= num <= 15:
                    if student not in progress:
                        progress[student] = {"done": [], "chat_id": chat_id}
                    if num not in progress[student]["done"]:
                        progress[student]["done"].append(num)
                        save_progress(progress)
                        send_telegram(chat_id, f"✅ Урок <b>{num}</b> закрыт для {student}!")
                    else:
                        send_telegram(chat_id, f"ℹ️ Урок <b>{num}</b> уже закрыт.")
                else:
                    send_telegram(chat_id, "⚠️ Номер урока от 1 до 15.")
            except ValueError:
                send_telegram(chat_id, "⚠️ Формат: /close 5")
        else:
            send_telegram(chat_id, "⚠️ Формат: /close <номер урока>")
        return

    if text.lower() in ("/help", "помощь"):
        send_telegram(chat_id,
            "📚 <b>Sunny English — Админ команды</b>\n\n"
            "/invite <b>имя</b> — создать инвайт-код для нового студента\n"
            "/close <b>номер</b> — закрыть урок для текущего студента (milasha)\n"
            "/status — прогресс по всем студентам\n"
            "/reset — сбросить весь прогресс\n"
            "/help — эта справка"
        )
        return

    try:
        num = int(text)
        student = "milasha"
        if 1 <= num <= 15:
            if student not in progress:
                progress[student] = {"done": [], "chat_id": chat_id}
            if num not in progress[student]["done"]:
                progress[student]["done"].append(num)
                save_progress(progress)
                send_telegram(chat_id, f"✅ Урок <b>{num}</b> закрыт для {student}!")
            else:
                send_telegram(chat_id, f"ℹ️ Урок <b>{num}</b> уже закрыт.")
        else:
            send_telegram(chat_id, "⚠️ Номер от 1 до 15 или /help")
    except ValueError:
        send_telegram(chat_id, "🤔 Не понял. /help — справка.")

STATIC_DIR = "/root/sunnyenglish"
MIME_TYPES = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/progress":
            student = parse_qs(parsed.query).get("student", ["milasha"])[0]
            data = load_progress()
            response_data = data.get(student, {"done": [], "chat_id": ""})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())
            return

        if parsed.path == "/api/verify":
            params = parse_qs(parsed.query)
            code = params.get("code", [""])[0]
            password = params.get("password", [""])[0]

            if password == ADMIN_PASSWORD:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "role": "admin"}).encode())
                return

            invite = verify_invite(code)
            if invite:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "role": "parent", "child": invite["child"]}).encode())
                return

            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": "Invalid code or password"}).encode())
            return

        if parsed.path == "/api/webhook":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
            return

        file_path = parsed.path.strip("/")
        if not file_path or file_path == "/":
            file_path = "lessons.html"
        full_path = os.path.join(STATIC_DIR, file_path)

        if os.path.isfile(full_path):
            ext = os.path.splitext(full_path)[1]
            content_type = MIME_TYPES.get(ext, "application/octet-stream")
            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/webhook":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))

            if "message" in body:
                handle_message(body["message"])
            elif "callback_query" in body:
                handle_callback(body["callback_query"])

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass

def poll_updates(offset=0):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
    try:
        with urllib.request.urlopen(url, timeout=35) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.error(f"Poll error: {e}")
        return {"ok": False, "result": []}

def poll_loop():
    offset = 0
    while True:
        try:
            result = poll_updates(offset)
            if result.get("ok"):
                for update in result.get("result", []):
                    offset = update["update_id"] + 1
                    if "message" in update:
                        handle_message(update["message"])
                    elif "callback_query" in update:
                        handle_callback(update["callback_query"])
        except Exception as e:
            log.error(f"Poll loop error: {e}")
        time.sleep(2)

if __name__ == "__main__":
    log.info(f"Starting Sunny Lessons server on :{PORT}")

    t = threading.Thread(target=poll_loop, daemon=True)
    t.start()

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()

#!/usr/bin/env python3
import json, base64, hashlib, threading, os, re, fcntl
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from urllib.request import urlopen, Request as URequest
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

ORDERS_FILE = os.environ.get('ORDERS_FILE', '/home/insite-api/orders.json')
ADMIN_PASS  = os.environ.get('ADMIN_PASS', '')
POST_TOKEN  = os.environ.get('POST_TOKEN', '')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', 'http://127.0.0.1:5678/webhook/insite/task')
LOCAL_API   = os.environ.get('LOCAL_API', 'http://127.0.0.1:9123/orders')

SITES_DIR    = os.environ.get('SITES_DIR', '/var/www/insite/sites')
PUBLIC_BASE  = 'https://bendernostur.duckdns.org:88/insite/sites'
ADMIN_CHAT_FILE = os.environ.get('ADMIN_CHAT_FILE', '/home/insite-api/admin_chat.txt')
TG_TOKEN     = os.environ.get('TELEGRAM_BOT_TOKEN', '')
GEMINI_KEY   = os.environ.get('GOOGLE_AI_API_KEY', '')
GEMINI_URL   = ('https://generativelanguage.googleapis.com/v1beta/models/'
                'gemini-2.5-flash:generateContent?key=' + GEMINI_KEY)

SITE_SYSTEM = (
    "You are a senior frontend developer at IN_SITE studio. "
    "Build a complete, production-ready, responsive single-page website. "
    "Output ONLY one self-contained HTML5 document with inline <style> and <script>. "
    "No markdown, no code fences, no explanations — start with <!DOCTYPE html> and end with </html>. "
    "IMPORTANT: Use the color palette, mood, and aesthetic from the client's reference images. "
    "If reference images show light/airy/pastel style — use those exact colors. "
    "Do NOT default to dark or grey — follow the references and the brief."
)

INTRO_CSS = """
<style>
@keyframes fadeIn   { from { opacity:0 } to { opacity:1 } }
@keyframes slideUp  { from { opacity:0; transform:translateY(20px) } to { opacity:1; transform:translateY(0) } }
@keyframes curtainReveal { 0% { clip-path: inset(0 50% 0 50%); } 100% { clip-path: inset(0 0 0 0); } }
@keyframes petal { 0%{transform:translateY(-10px) rotate(0deg);opacity:1} 100%{transform:translateY(60px) rotate(180deg);opacity:0} }
.intro-fade { animation: fadeIn 1.5s ease-in-out both; }
.intro-slide { animation: slideUp 1.2s ease both; }
.intro-curtain { animation: curtainReveal 2s ease-in-out both; overflow: hidden; }
.intro-petals { position: relative; overflow: hidden; }
.intro-petals::before, .intro-petals::after {
  content: '🌸'; position: absolute; font-size: 24px;
  animation: petal 2.5s ease-in infinite;
}
.intro-petals::before { left: 20%; animation-delay: 0s; }
.intro-petals::after  { left: 70%; animation-delay: .8s; }
.intro-countdown { animation: fadeIn 1s ease-in-out both; }
</style>"""

INTRO_WRAPPER = {
    'fade':       ('<div class="intro-fade">',       '</div>'),
    'slide':      ('<div class="intro-slide">',      '</div>'),
    'curtain':    ('<div class="intro-curtain">',    '</div>'),
    'petals':     ('<div class="intro-petals">',     '</div>'),
    'countdown':  ('<div class="intro-countdown">',  '</div>'),
}

def build_site(brief, order_id, references=None, intro='none'):
    """Call Gemini, extract a full HTML document, write it to disk, return public URL."""
    user_parts = []
    if references:
        for ref in references[:4]:
            data_url = ref.get('data', '')
            if not data_url.startswith('data:'):
                continue
            try:
                mime = data_url.split(';')[0].replace('data:', '')
                b64 = data_url.split(',', 1)[1]
                if len(b64) > 8_000_000:
                    continue
                user_parts.append({"inline_data": {"mime_type": mime, "data": b64}})
            except Exception:
                continue
        if user_parts:
            user_parts.append({"text": "Вот референсные изображения от клиента. Изучи стиль, цвета, настроение и воспроизведи их в сайте.\n\n" + brief})
        else:
            user_parts = [{"text": brief}]
    else:
        user_parts = [{"text": brief}]

    payload = json.dumps({
        "systemInstruction": {"parts": [{"text": SITE_SYSTEM}]},
        "contents": [{"role": "user", "parts": user_parts}],
        "generationConfig": {"maxOutputTokens": 65536, "temperature": 0.8},
    }).encode()
    req = URequest(GEMINI_URL, data=payload, headers={'Content-Type': 'application/json'})
    raw = urlopen(req, timeout=180).read().decode('utf-8', errors='replace')
    data = json.loads(raw)
    if data.get('error'):
        raise RuntimeError('Gemini: ' + json.dumps(data['error'])[:300])
    parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
    text = ''.join(p.get('text', '') for p in parts) or ''
    m = re.search(r'<!DOCTYPE html.*?</html>', text, re.IGNORECASE | re.DOTALL)
    if not m:
        m = re.search(r'<html.*?</html>', text, re.IGNORECASE | re.DOTALL)
    html = m.group(0) if m else text.replace('```html', '').replace('```', '').strip()
    if '<html' not in html.lower():
        raise RuntimeError('agent did not return HTML')
    if intro and intro != 'none' and intro in INTRO_WRAPPER:
        html = html.replace('<head>', '<head>' + INTRO_CSS, 1)
        wrap_open, wrap_close = INTRO_WRAPPER[intro]
        html = re.sub(r'<body[^>]*>', lambda m: m.group(0) + wrap_open, html, count=1, flags=re.IGNORECASE)
        html = html.replace('</body>', wrap_close + '</body>', 1)
    out_dir = os.path.join(SITES_DIR, order_id)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'index.html'), 'w') as f:
        f.write(html)
    return PUBLIC_BASE + '/' + order_id + '/'

_orders_lock = threading.Lock()

def load_orders():
    try:
        with open(ORDERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_orders(orders):
    tmp = ORDERS_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ORDERS_FILE)

def patch_order(order_id, patch):
    with _orders_lock:
        orders = load_orders()
        for o in orders:
            if o.get('id') == order_id:
                for k, v in patch.items():
                    if k == 'agent_notes':
                        o.setdefault('agent_notes', [])
                        o['agent_notes'].extend(v)
                    else:
                        o[k] = v
                break
        save_orders(orders)

def md2(s):
    """Escape text for Telegram MarkdownV2."""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(s))

def tg_notify_order(order):
    """Push a short Telegram alert to the registered admin chat on a new order."""
    if not TG_TOKEN:
        return
    try:
        chat = open(ADMIN_CHAT_FILE).read().strip()
    except:
        return
    if not chat:
        return
    sec   = order.get('section', '—')
    name  = order.get('couple_names') or order.get('client_name') or order.get('event_name') or '—'
    email = order.get('client_email', '—')
    tpl   = (order.get('template') or {}).get('name', '—')
    oid   = order.get('id', '?')
    text  = (f"📥 *Новая заявка* \\[{md2(sec)}\\]\n\n"
             f"👤 {md2(name)}\n✉️ {md2(email)}\n🎨 {md2(tpl)}\n🆔 `{oid}`\n\n"
             f"`/build {oid}` — собрать сайт\n/orders — все заявки")
    payload = json.dumps({'chat_id': chat, 'text': text, 'parse_mode': 'MarkdownV2'}).encode()
    def _send():
        try:
            req = URequest(f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage',
                           data=payload, headers={'Content-Type': 'application/json'})
            urlopen(req, timeout=15)
        except Exception as e:
            print(f"[tg] notify error: {e}")
    threading.Thread(target=_send, daemon=True).start()

def notify_manager(order):
    sec    = order.get('section', 'wedding')
    name   = order.get('couple_names') or order.get('client_name') or order.get('event_name') or '—'
    email  = order.get('client_email', '—')
    phone  = order.get('phone', '')
    tpl    = (order.get('template') or {}).get('name', '—')
    niche  = order.get('niche') or order.get('specialization') or order.get('event_type') or ''
    budget = order.get('budget', '—')
    notes  = order.get('extra_notes') or order.get('style_notes') or ''
    oid    = order.get('id', '?')

    lines = [
        f"📥 Новая заявка [{sec.upper()}] #{oid}",
        f"Имя: {name}",
        f"Email: {email}",
    ]
    if phone:  lines.append(f"Тел: {phone}")
    if niche:  lines.append(f"Ниша: {niche}")
    lines.append(f"Шаблон: {tpl}")
    lines.append(f"Бюджет: {budget}")
    if notes:  lines.append(f"Пожелания: {notes[:200]}")
    lines.append(f"\nОткрыть в админке: https://bendernostur.duckdns.org:88/insite/admin.html")

    payload = json.dumps({
        "department": "creative_manager",
        "task": "\n".join(lines),
        "context": "E-T-E LABORATORY — IN_SITE Studio. Новая заявка от клиента.",
        "order_id": oid,
        "section": sec,
    }).encode()

    def _send():
        try:
            req = URequest(WEBHOOK_URL, data=payload,
                           headers={'Content-Type': 'application/json'})
            resp = urlopen(req, timeout=60)
            raw = resp.read().decode('utf-8', errors='replace')
            try:
                data = json.loads(raw)
                items = data if isinstance(data, list) else [data]
                notes = []
                for item in items:
                    result = item.get('result') or item.get('text') or item.get('output') or str(item)
                    dept   = item.get('department', 'creative_manager')
                    model  = item.get('model', '')
                    if result and result.strip():
                        notes.append({
                            'department': dept,
                            'model': model,
                            'text': result.strip(),
                            'ts': datetime.now().isoformat(),
                        })
                if notes:
                    patch_order(oid, {'agent_notes': notes})
            except Exception as e:
                print(f"[notify] parse error: {e} | raw: {raw[:200]}")
        except Exception as e:
            print(f"[notify] webhook error: {e}")

    threading.Thread(target=_send, daemon=True).start()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def check_basic_auth(self):
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Basic '):
            return False
        try:
            decoded = base64.b64decode(auth[6:]).decode()
            user, pw = decoded.split(':', 1)
            return user == 'root' and pw == ADMIN_PASS
        except:
            return False

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-INSITE-KEY, Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/telegram-config':
            self._json(200, {"token": TG_TOKEN})
            return
        if self.path != '/orders':
            self.send_response(404); self.end_headers(); return
        if not self.check_basic_auth():
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm=IN_SITE')
            self.send_cors(); self.end_headers(); return
        orders = load_orders()
        body = json.dumps(orders, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_cors()
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path == '/admin_chat':
            if not self.check_basic_auth():
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm=IN_SITE')
                self.send_cors(); self.end_headers(); return
            length = int(self.headers.get('Content-Length', 0))
            try:
                data = json.loads(self.rfile.read(length))
                chat = str(data['chat_id'])
            except:
                self._json(400, {'ok': False, 'error': 'chat_id required'}); return
            with open(ADMIN_CHAT_FILE, 'w') as f:
                f.write(chat)
            self._json(200, {'ok': True, 'chat_id': chat}); return
        if self.path == '/build':
            if not self.check_basic_auth():
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm=IN_SITE')
                self.send_cors(); self.end_headers(); return
            length = int(self.headers.get('Content-Length', 0))
            try:
                data = json.loads(self.rfile.read(length))
            except:
                self._json(400, {'ok': False, 'error': 'bad json'}); return
            brief = (data.get('brief') or '').strip()
            order_id = (data.get('order_id') or hashlib.md5(brief.encode()).hexdigest()[:12])
            references = data.get('references') or None
            intro = data.get('intro') or 'none'
            if references is None and order_id:
                for o in load_orders():
                    if o.get('id') == order_id:
                        references = o.get('references') or None
                        intro = o.get('intro') or intro
                        break
            if not brief:
                self._json(400, {'ok': False, 'error': 'brief required'}); return
            try:
                url = build_site(brief, order_id, references=references, intro=intro)
                if any(o.get('id') == order_id for o in load_orders()):
                    patch_order(order_id, {'site_url': url, 'status': 'built'})
                self._json(200, {'ok': True, 'order_id': order_id, 'url': url})
            except Exception as e:
                self._json(500, {'ok': False, 'error': str(e)})
            return
        if self.path != '/orders':
            self.send_response(404); self.end_headers(); return
        token = self.headers.get('X-INSITE-KEY', '')
        if token != POST_TOKEN:
            self.send_response(403); self.send_cors(); self.end_headers(); return
        length = int(self.headers.get('Content-Length', 0))
        try:
            data = json.loads(self.rfile.read(length))
        except:
            self.send_response(400); self.send_cors(); self.end_headers(); return
        if 'id' not in data:
            data['id'] = hashlib.md5((str(datetime.now()) + data.get('client_email','')).encode()).hexdigest()[:12]
        data.setdefault('status', 'new')
        data.setdefault('read', False)
        data.setdefault('submitted_at', datetime.now().isoformat())
        orders = load_orders()
        is_new = not any(o.get('id') == data['id'] for o in orders)
        if is_new:
            orders.append(data)
            save_orders(orders)
            notify_manager(data)
            tg_notify_order(data)
        resp = json.dumps({'ok': True, 'id': data['id']}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resp))
        self.send_cors()
        self.end_headers()
        self.wfile.write(resp)

    def do_PATCH(self):
        if not self.path.startswith('/orders/'):
            self.send_response(404); self.end_headers(); return
        if not self.check_basic_auth():
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm=IN_SITE')
            self.send_cors(); self.end_headers(); return
        order_id = self.path[8:]
        length = int(self.headers.get('Content-Length', 0))
        try:
            patch = json.loads(self.rfile.read(length))
        except:
            self.send_response(400); self.send_cors(); self.end_headers(); return
        patch_order(order_id, {k: v for k, v in patch.items()
                                if k in ('status', 'read', 'revisions', 'agent_notes', 'site_url', 'site_content')})
        # If site_content provided, save to file
        site_content = patch.get('site_content')
        if site_content:
            out_dir = os.path.join(SITES_DIR, order_id)
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(site_content)
        resp = json.dumps({'ok': True}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_cors()
        self.end_headers()
        self.wfile.write(resp)


    def do_DELETE(self):
        if not self.path.startswith('/orders/'):
            self.send_response(404); self.end_headers(); return
        if not self.check_basic_auth():
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm=IN_SITE')
            self.send_cors(); self.end_headers(); return
        order_id = self.path[8:]
        orders = load_orders()
        new_orders = [o for o in orders if o.get('id') != order_id]
        if len(new_orders) == len(orders):
            self._json(404, {'ok': False, 'error': 'not found'}); return
        save_orders(new_orders)
        self._json(200, {'ok': True})

if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 9123), Handler)
    print('IN_SITE API listening on :9123')
    server.serve_forever()

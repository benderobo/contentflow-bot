#!/usr/bin/env python3
import json, os, io, mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

TELEGRAM_BOT_TOKEN = '8655259510:AAGd1iMvLL_ZZw77j2O8RXztspq94Xd2HtM'
TELEGRAM_CHAT_ID = '1139186144'
PORT = 8090


def generate_act_html(data):
    name = data.get('name', '')
    phone = data.get('phone', '')
    email = data.get('email', 'не указан')
    child = data.get('child', 'не указано')
    now = datetime.now()
    date_str = now.strftime('%d.%m.%Y')
    act_num = f"Акт-{now.year}-{now.month:02d}-{now.day:02d}-{os.urandom(2).hex().upper()}"

    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">
<title>Акт об уничтожении ПДн {act_num}</title>
<style>body{{font-family:'Times New Roman',serif;max-width:700px;margin:40px auto;padding:20px;line-height:1.8;color:#000;}}
h1{{font-size:1.3rem;text-align:center;margin-bottom:30px;}}h2{{font-size:1.1rem;margin:20px 0 10px;}}p{{margin:8px 0;}}
table{{width:100%;border-collapse:collapse;margin:16px 0;}}td{{border:1px solid #000;padding:8px 12px;font-size:0.95rem;}}
.signature{{margin-top:40px;display:flex;justify-content:space-between;}}.signature div{{width:45%;}}
.signature p{{border-top:1px solid #000;margin-top:60px;padding-top:4px;font-size:0.9rem;}}
@media print{{body{{margin:0;padding:20mm;}}}}</style></head><body>
<h1>АКТ<br>об уничтожении персональных данных</h1>
<p><strong>г. ________________</strong> &emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp;&emsp; <strong>{date_str}</strong></p>
<h2>1. Сведения о субъекте персональных данных</h2>
<table><tr><td>ФИО родителя (законного представителя)</td><td>{name}</td></tr>
<tr><td>Телефон</td><td>{phone}</td></tr>
<tr><td>E-mail</td><td>{email}</td></tr>
<tr><td>Имя ребёнка</td><td>{child}</td></tr></table>
<h2>2. Основание для уничтожения</h2>
<p>Отзыв согласия на обработку персональных данных в соответствии с Федеральным законом от 27.07.2006 №152-ФЗ «О персональных данных».</p>
<h2>3. Перечень уничтоженных персональных данных</h2>
<table><tr><td>Имя ребёнка</td><td>удалено</td></tr>
<tr><td>Имя родителя (законного представителя)</td><td>удалено</td></tr>
<tr><td>Контактный телефон</td><td>удалено</td></tr></table>
<h2>4. Способ и срок уничтожения</h2>
<p>Данные удалены из всех баз данных и систем Оператора без возможности восстановления. Уничтожение выполнено в день подписания настоящего акта.</p>
<p>Номер акта: {act_num}</p>
<div class="signature">
<div><p>Оператор<br><br>________________ / _______________ /</p></div>
<div><p>Субъект персональных данных<br><br>________________ / {name} /</p></div>
</div></body></html>""", act_num


def send_telegram_document(html_content, act_num, text_msg):
    boundary = '----FormBoundary' + os.urandom(16).hex()
    lines = []

    def add_field(name, value):
        lines.append(f'--{boundary}')
        lines.append(f'Content-Disposition: form-data; name="{name}"')
        lines.append('')
        lines.append(value)

    add_field('chat_id', TELEGRAM_CHAT_ID)
    add_field('caption', text_msg)
    add_field('parse_mode', 'Markdown')

    lines.append(f'--{boundary}')
    lines.append(f'Content-Disposition: form-data; name="document"; filename="{act_num}.html"')
    lines.append('Content-Type: text/html')
    lines.append('')
    lines.append(html_content)

    lines.append(f'--{boundary}--')
    body = '\r\n'.join(lines).encode('utf-8')

    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument'
    req = Request(url, data=body, method='POST')
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    resp = urlopen(req, timeout=30)
    return json.loads(resp.read().decode())


def send_telegram_text(text_msg):
    payload = json.dumps({
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text_msg,
        'parse_mode': 'Markdown'
    }).encode()
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    req = Request(url, data=payload, method='POST')
    req.add_header('Content-Type', 'application/json')
    urlopen(req, timeout=15)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.end_headers()

    def do_POST(self):
        if self.path != '/revoke':
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get('Content-Length', 0))
        try:
            data = json.loads(self.rfile.read(length))
        except Exception:
            self.send_response(400)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': False, 'error': 'bad json'}).encode())
            return

        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip() or 'не указан'
        child = data.get('child', '').strip() or 'не указано'

        html_content, act_num = generate_act_html(data)

        now = datetime.now()
        date_str = now.strftime('%d.%m.%Y')
        text_msg = (
            f"⚠️ *Отзыв согласия на обработку ПДн*\n\n"
            f"👤 Родитель: *{name}*\n"
            f"📞 Телефон: *{phone}*\n"
            f"📧 E-mail: {email}\n"
            f"👶 Ребёнок: {child}\n\n"
            f"📋 Акт: `{act_num}`\n"
            f"📅 Дата: {date_str}\n\n"
            f"Необходимо уничтожить персональные данные в течение 30 рабочих дней."
        )

        try:
            send_telegram_text(text_msg)
        except Exception as e:
            print(f"[tg] text error: {e}")

        try:
            result = send_telegram_document(html_content, act_num, text_msg)
            resp = {'ok': True, 'act_num': act_num}
        except Exception as e:
            print(f"[tg] document error: {e}")
            resp = {'ok': True, 'act_num': act_num, 'doc_sent': False, 'error': str(e)}

        body = json.dumps(resp, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), Handler)
    print(f'Sunny English revoke API on :{PORT}')
    server.serve_forever()

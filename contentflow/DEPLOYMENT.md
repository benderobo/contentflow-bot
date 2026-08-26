# Развертывание ContentFlow Bot

## 🚀 Quick Start (5 минут)

### Локально (для разработки)

```bash
# 1. Клонирование
git clone https://github.com/benderobo/contentflow.git
cd contentflow

# 2. Конфигурация
cp .env.example .env
# Отредактируйте .env

# 3. Запуск Docker
docker compose up -d

# 4. Инициализация БД
docker compose exec api alembic upgrade head

# 5. Тестирование
docker compose exec bot pytest tests/

# 6. Бот готов!
# Откройте Telegram и найдите своего бота
```

## 🖥️ Production VPS Deployment

### Требования

- VPS с 2+ ядрами, 4GB+ RAM
- Ubuntu 22.04 LTS или CentOS 8+
- Docker & Docker Compose
- Nginx (reverse proxy)
- SSL сертификат

### Шаг 1: Подготовка сервера

```bash
# SSH на сервер
ssh root@your-vps-ip

# Обновить систему
apt update && apt upgrade -y

# Установить Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER

# Установить Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Проверить версии
docker --version
docker-compose --version
```

### Шаг 2: Клонирование и конфигурация

```bash
# Перейти в /opt
cd /opt

# Клонировать репозиторий
git clone https://github.com/benderobo/contentflow.git
cd contentflow

# Создать .env из примера
cp .env.example .env

# Отредактировать конфигурацию
nano .env
```

### Шаг 3: Запуск сервиса

```bash
# Запустить все контейнеры
docker compose up -d

# Проверить статус
docker compose ps

# Просмотр логов
docker compose logs -f bot
```

### Шаг 4: Nginx конфигурация

Создайте `/etc/nginx/sites-available/contentflow`:

```nginx
upstream api {
    server 127.0.0.1:8000;
}

upstream web {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Редирект на HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL сертификаты
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Web Dashboard
    location / {
        proxy_pass http://web;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API
    location /api/ {
        proxy_pass http://api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # WebSocket поддержка
    location /ws/ {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Кэширование статики
    location ~* \.(js|css|png|jpg|gif|ico)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Активируйте конфиг:

```bash
ln -s /etc/nginx/sites-available/contentflow /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### Шаг 5: SSL сертификат (Let's Encrypt)

```bash
apt install certbot python3-certbot-nginx -y

# Получить сертификат
certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
systemctl enable certbot.timer
```

### Шаг 6: Systemd сервис (автозапуск)

Создайте `/etc/systemd/system/contentflow.service`:

```ini
[Unit]
Description=ContentFlow Bot
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/contentflow
ExecStart=/usr/local/bin/docker-compose up
ExecStop=/usr/local/bin/docker-compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активируйте:

```bash
systemctl daemon-reload
systemctl enable contentflow
systemctl start contentflow
systemctl status contentflow
```

## 📊 Мониторинг

### Health Check

```bash
# API
curl https://yourdomain.com/api/health

# Bot
docker compose logs bot | tail -20
```

### Метрики (опционально)

Добавьте Prometheus endpoint в `api/main.py`:

```python
from prometheus_client import Counter, Histogram, generate_latest

# Метрики
post_published = Counter('posts_published_total', 'Total posts published')
ai_requests = Histogram('ai_requests_duration_seconds', 'AI request duration')

@app.get("/metrics")
async def metrics():
    return generate_latest()
```

### Логирование (опционально)

Отправляйте логи в ELK Stack или CloudWatch:

```python
import logging
from pythonjsonlogger import jsonlogger

handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
```

## 🔄 Обновление

```bash
cd /opt/contentflow

# Получить новые изменения
git pull origin main

# Пересобрать образы
docker compose build

# Перезапустить сервисы
docker compose up -d
```

## 🗑️ Очистка

```bash
# Остановить контейнеры
docker compose down

# Удалить образы
docker compose down -v

# Удалить хранилище
rm -rf storage/

# Полная очистка
docker system prune -a
```

## 🔧 Maintenance

### Резервная копия БД

```bash
# Локальная
docker compose exec postgres pg_dump -U contentflow contentflow > backup.sql

# Восстановление
docker compose exec -T postgres psql -U contentflow contentflow < backup.sql
```

### Проверка логов

```bash
# Все сервисы
docker compose logs -f

# Конкретный сервис
docker compose logs -f worker

# Последние N строк
docker compose logs --tail=100 bot
```

### Перезагрузка сервиса

```bash
# Мягкий перезапуск
docker compose restart worker

# Жесткий перезапуск
docker compose down
docker compose up -d
```

## 🆘 Troubleshooting

### Bot не отвечает

```bash
# Проверить статус
docker compose ps bot

# Просмотреть логи
docker compose logs bot | tail -50

# Перезапустить
docker compose restart bot
```

### Ошибки БД

```bash
# Проверить соединение
docker compose exec postgres psql -U contentflow

# Проверить миграции
docker compose exec api alembic current
```

### Worker не обрабатывает задачи

```bash
# Проверить задачи в очереди
docker compose exec redis redis-cli KEYS '*'

# Перезапустить worker
docker compose restart worker

# Проверить Celery статус
docker compose exec worker celery -A workers.tasks inspect active
```

### Проблемы с памятью

```bash
# Проверить использование
docker stats

# Увеличить лимиты в docker-compose.yml
services:
  worker:
    deploy:
      resources:
        limits:
          memory: 2G
```

## 📈 Масштабирование

### Несколько workers

```bash
# Запустить 4 worker инстанса
docker compose up -d --scale worker=4
```

### Load balancing

Используйте Nginx upstream для распределения нагрузки на несколько API инстансов.

## 🔒 Security Hardening

```bash
# Отключить SSH пароли
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

# Firewall (ufw)
ufw enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw default deny incoming

# Fail2ban (защита от brute-force)
apt install fail2ban -y
systemctl enable fail2ban
```

---

**Поздравляем! ContentFlow Bot развернут и готов к работе! 🎉**

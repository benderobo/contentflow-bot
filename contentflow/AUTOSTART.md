# ⚙️ Автозапуск ContentFlow Bot после перезагрузок

## 📋 Вариант 1: systemd (Linux) - Рекомендуется

### Шаг 1: Установить сервис

```bash
# Скопировать systemd unit файл
sudo cp docker/contentflow.service /etc/systemd/system/

# Обновить systemd
sudo systemctl daemon-reload

# Включить автозапуск
sudo systemctl enable contentflow.service

# Запустить сервис
sudo systemctl start contentflow.service
```

### Шаг 2: Проверить статус

```bash
# Статус
sudo systemctl status contentflow.service

# Логи
sudo journalctl -u contentflow.service -f
```

### Управление

```bash
# Остановить
sudo systemctl stop contentflow.service

# Перезагрузить
sudo systemctl restart contentflow.service

# Отключить автозапуск
sudo systemctl disable contentflow.service

# Удалить
sudo rm /etc/systemd/system/contentflow.service
sudo systemctl daemon-reload
```

---

## 📋 Вариант 2: Docker Restart Policy (самый простой)

Сервис уже настроен с `restart: always` в docker-compose.yml

```bash
# Просто запустить один раз
docker compose up -d

# Docker автоматически перезагрузит контейнеры после:
# - Перезагрузки машины
# - Падения контейнера
# - Перезагрузки Docker daemon
```

Это работает "из коробки" - ничего дополнительно делать не нужно! ✅

---

## 📋 Вариант 3: Cron Job (Linux)

Если systemd не подходит:

```bash
# Открыть crontab
crontab -e

# Добавить строку (запуск каждый час, проверка что сервис жив):
@reboot cd /path/to/contentflow && docker compose up -d

# Или каждые 5 минут проверять статус:
*/5 * * * * cd /path/to/contentflow && docker compose up -d
```

---

## 📋 Вариант 4: Docker Desktop (Windows/Mac)

**Settings → General → Start Docker Desktop when you log in**

Docker Desktop сам поднимет контейнеры с `restart: always`.

---

## ✅ Проверить автозапуск

### Linux (systemd):
```bash
sudo systemctl is-enabled contentflow.service
# Должен вывести: enabled
```

### Docker restart policy:
```bash
docker compose ps
# Все контейнеры должны быть в статусе "Up"

# Даже после:
docker compose restart
# или
sudo reboot
```

---

## 🔍 Диагностика

### Если не запустилось после перезагрузки:

```bash
# Проверить статус systemd сервиса
sudo systemctl status contentflow.service

# Посмотреть ошибки
sudo journalctl -u contentflow.service | tail -100

# Проверить Docker статус
docker ps -a

# Проверить логи контейнера
docker compose logs
```

### Если контейнер крашится:

```bash
# Посмотреть логи
docker compose logs -f bot

# Проверить ресурсы
docker stats

# Перезагрузить контейнер
docker compose restart bot
```

---

## 🎯 Рекомендуемая настройка

**Для Linux VPS:**
1. Используйте **systemd** (Вариант 1)
2. Добавьте в systemd `Restart=always`
3. Настройте логирование через journalctl

**Для локального ПК:**
1. Docker Desktop с `Start on login`
2. Docker Compose с `restart: always`
3. Вуаля - работает! 🎉

**Для production:**
1. systemd + monitoring
2. Backup стратегия
3. Health checks

---

## 📝 Текущая конфигурация

В `docker-compose.yml` уже установлено:

```yaml
services:
  bot:
    restart: always          # ✅ Перезапуск при ошибке
    restart_policy:
      condition: any         # ✅ Всегда перезапускать
      delay: 10s             # ✅ Задержка перед перезапуском
```

**Это значит:**
- ✅ Контейнер перезагружается при падении
- ✅ Контейнер стартует при перезагрузке Docker
- ✅ Контейнер стартует при перезагрузке ОС (если Docker запустился)

---

**Выберите удобный для вас вариант и готово!** 🚀

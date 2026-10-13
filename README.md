# ContentFlow Bot

Автоматическая система управления контентом для Telegram-каналов: парсинг источников → анализ → AI-рерайт → редактирование → модерация → планирование → публикация.

Код проекта и инструкция по запуску — в [`contentflow/`](./contentflow/README.md).

## Что в репозитории

| Путь | Назначение |
|---|---|
| [`contentflow/`](./contentflow/) | Бот, API, воркеры, миграции, Docker-образы |
| [`docker/contentflow.service`](./docker/contentflow.service) | systemd-юнит для запуска через Docker Compose |
| [`.env.example`](./.env.example) | Шаблон переменных окружения (настоящий `.env` в git не кладётся) |
| `AUDIT_REPORT.md`, `ERRORS.md`, `FINAL_VALIDATION.md`, `RECOVERY_REPORT.md` | Аудит, журнал ошибок, итоговая проверка и отчёт о восстановлении |
| [`kill_error.md`](./kill_error.md) | Журнал инцидентов проекта |
| [`.claude/CLAUDE.md`](./.claude/CLAUDE.md) | Правила безопасности для работы с репозиторием |

## Безопасность

`.env`, токены ботов, ключи API и пароли БД не коммитятся. Перед каждым коммитом: `git status` не должен содержать `.env`, а `git diff --cached` — реальных секретов (см. `.claude/CLAUDE.md`).

## История репозитория

Раньше здесь лежали и посторонние проекты (мини-приложение с играми, IN_SITE Studio, SunnyEnglish, telegram-brain); они вынесены в отдельные репозитории. Полная история остаётся доступной в git.

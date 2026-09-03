# План: список статей → miniapp-редактор + быстрый режим замены канала

## Context
Сейчас после парсинга источника (`bot/source_handlers.py:352-387 handle_source_parse_all`) пользователь видит только счётчики ("найдено N статей"), но не может открыть конкретную статью. Editor уже существует как отдельное React-приложение (`web/`) с кнопкой `web_app=WebAppInfo(...)` в `bot/handlers.py:318-321`, но это по сути демо-заглушка: URL захардкожен на `http://localhost:3000`, доступ ограничен одним хардкод-`user_id`, initData не проверяется на бэкенде, и редактор не знает про конкретный `SourceItem` — работает только с абстрактным Post.

Нужно: (1) превратить список распарсенных статей в реальную точку входа — по клику на статью открывается miniapp-редактор с текстом именно этой статьи и AI-переписыванием; (2) добавить в редактор "быстрый режим" — переключатель, который в тексте убирает упоминания одного канала (заданного пользователем) и подставляет упоминания другого.

Попутно чиним инфраструктуру miniapp (URL из конфига, доступ всем пользователям, валидация initData) — без этого фича 1 не заработает для реальных пользователей.

## Часть A — Инфраструктура Mini App

1. **`core/config.py`** — добавить `webapp_url: str` (например default `http://localhost:3000`, переопределяется через `.env` → `WEBAPP_URL`). Прописать в `.env` / `.env.example`.
2. **`bot/handlers.py:318-321`** — убрать проверку хардкод `user_id == 5264530602`, кнопка редактора доступна всем; URL берём из `settings.webapp_url`.
3. **Валидация initData на бэкенде.** Добавить утилиту `verify_webapp_init_data(init_data: str, bot_token: str) -> Optional[dict]` (HMAC-SHA256 проверка по алгоритму Telegram, аналогично `utils/auth.py` где уже есть `sign_user_id/verify_user_id` — используем тот же файл или соседний `utils/webapp_auth.py`). Новый API-эндпоинт(ы) для miniapp принимают `init_data` в заголовке/теле и валидируют вместо самодельной `user_id+user_signature` схемы, которая используется в остальном API.
4. **Раздача статики** — не трогаем существующий nginx/Dockerfile для `web/`, оставляем раздачу отдельным сервисом (не через FastAPI), но URL параметризуем.

## Часть B — Список статей после парсинга + отдельная кнопка

1. **`bot/source_handlers.py`**
   - В `handle_source_parse_all` (352-387): после парсинга сразу показывать инлайн-список найденных статей (не только счётчики) — переиспользовать новую функцию рендера списка (см. ниже).
   - Новая функция `render_items_list(user_id, source_id=None)`, вызывающая `GET /api/sources/items/unanalyzed` (уже есть, `api/routes/sources.py:202-252`, но пока лимит=5 и без привязки к источнику — расширить query-параметром `source_id` опционально и увеличить limit/добавить пагинацию по 5-10 шт.).
   - Кнопки: `[InlineKeyboardButton(text=item.title[:60], callback_data=f"item_open_{item.id}")]` для каждой статьи.
   - Новая отдельная кнопка **"📰 Статьи"** в меню источника (`handle_source_settings` или меню `menu_sources` в `handlers.py`) — открывает тот же список по требованию, не только сразу после парсинга.

2. **Callback `item_open_{id}`** — новый хендлер в `source_handlers.py`:
   - Отправляет сообщение с одной кнопкой "✏️ Открыть в редакторе" через `web_app=WebAppInfo(url=f"{settings.webapp_url}?item_id={id}")` — стандартный способ передать id статьи в miniapp через query string.

3. **API: получение статьи для редактора.** Новый эндпоинт `GET /api/sources/items/{item_id}` (в `api/routes/sources.py`), защищённый валидацией initData (Часть A.3) — отдаёт `title/description/content` конкретного `SourceItem`.

4. **API: сохранение как Post.** Существующий `POST /api/posts` (`api/routes/posts.py:82-112`) уже принимает `source_item_id` — редактор просто вызывает его при сохранении, доп. эндпоинт конвертации не нужен.

## Часть C — React-редактор (`web/`)

1. **`web/src/App.tsx`** — читать `item_id` из query string (`URLSearchParams`), при наличии — грузить `GET /api/sources/items/{item_id}` вместо пустой формы Post; передавать `initData` (из `window.Telegram.WebApp.initData`) в заголовке всех запросов к API.
2. **`web/src/components/Toolbar.tsx`** — добавить переключатель "⚡ Быстрый режим" с двумя текстовыми полями (старое упоминание / новое упоминание, например `@old_channel` → `@new_channel`), кнопка "Применить" вызывает AI rewrite с доп. параметром.
3. **AI rewrite с заменой каналов.**
   - `api/routes/ai.py` — расширить `POST /api/ai/rewrite` (строка 274) опциональными полями `replace_from: Optional[str]`, `replace_to: Optional[str]`.
   - `services/ai.py: AIService.rewrite_content` (строка 194) — принять доп. параметры, при наличии дописывать в промпт инструкцию вида: `f"Remove all mentions of '{replace_from}' and replace them with '{replace_to}' where contextually appropriate."` перед основным rewrite-промптом.
   - MockProvider (для тестового прогона) — добавить простую текстовую замену `text.replace(replace_from, replace_to)` в дополнение к текущим префиксам, чтобы функциональность была проверяема без реального AI-ключа.

## Проверка (end-to-end)
1. Пересобрать/перезапустить контейнеры `contentflow-api`, `contentflow-bot`, и webapp-контейнер (если меняется `web/`).
2. Через curl: добавить источник → `/api/sources/parse-all` → убедиться, что `/api/sources/items/unanalyzed?source_id=...` возвращает статьи.
3. В Telegram: запустить парсинг вручную → проверить, что бот показывает список статей кнопками, и отдельную кнопку "📰 Статьи" в меню источника.
4. Открыть miniapp по клику на статью — проверить, что редактор загружает именно текст этой статьи (curl-эмуляция `GET /api/sources/items/{id}` с валидным/невалидным `init_data` — 200 vs 401/403).
5. В редакторе включить "Быстрый режим", ввести старое/новое упоминание, применить AI rewrite (Mock-провайдер) — проверить, что упоминания заменились в результате.
6. Сохранить как пост (`POST /api/posts` с `source_item_id`) — проверить появление поста в списке черновиков бота.

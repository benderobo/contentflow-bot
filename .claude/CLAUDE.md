# ContentFlow Bot — Project-Specific Security Rules

## 🚨 CRITICAL: Never Commit .env or Secrets to Git

**STOP перед любым git commit если:**
- В `git diff --cached` есть `.env` файл
- Есть реальные API ключи: `sk-`, `api_key`, `token`, `secret`, `OPENROUTER_API_KEY` и т.п.
- Есть пароли БД, учетные данные, приватные ключи

**Проверка перед коммитом:**
```bash
git diff --cached | grep -E "sk-|api_key|token|secret|OPENROUTER|DATABASE_PASSWORD"
```
Если что-то найдено → `git reset HEAD <file>` и отстейдж файл.

**Правило .gitignore:**
- `.env` должен быть в `.gitignore` — проверь перед первым коммитом
- Если .env закоммитен случайно → `git reset --hard <safe-commit>` чтобы удалить из истории

**Если случайно запушил в origin:**
1. 🔴 НЕМЕДЛЕННО ротируй **ВСЕ** скомпрометированные ключи
2. В этом проекте: OPENROUTER_API_KEY нужно ротировать на https://openrouter.ai/settings/keys
3. Обнови .env локально с новыми ключами
4. Перезагрузи контейнеры: `docker restart contentflow-api contentflow-bot`

**Real incident:** Случайно закоммитил OPENROUTER_API_KEY в коммит 0e5558d. GitHub Push Protection заблокировал пуш, но ключ был уже в коммите. Удалил коммит из локальной истории через `git reset --hard`, но пришлось бы ротировать ключ если бы запушилось.

---

**Всегда:**
- ✅ Используй `.env.example` вместо `.env` для шаблона (сохрани в git)
- ✅ Проверяй `git status` перед коммитом — не должно быть `.env`
- ✅ Ограничивай доступ к реальным .env файлам
- ✅ Логируй инциденты в kill_error.md

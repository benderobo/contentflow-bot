# ContentFlow Bot - E2E Test Plan

## Pre-requisites
- Docker Compose stack running
- PostgreSQL initialized
- Redis available
- Valid Telegram bot token (BOT_TOKEN)
- Valid AI API key (if testing AI features)

## Test Scenarios

### Scenario 1: RSS Source Parsing
**Purpose**: Verify that RSS sources can be parsed and content items created

1. **Setup**:
   - Create a test user in Telegram (or use existing)
   - Add a public RSS feed as source via bot command `/add_source`
   - Select "RSS" type
   - Provide valid RSS feed URL

2. **Execution**:
   - Trigger parse_source Celery task manually or wait for scheduler
   - Monitor logs for parse success

3. **Verification**:
   - Check `source_items` table has new rows
   - Verify `title`, `description`, `original_url` are populated
   - Verify `content_hash` is calculated
   - Verify no duplicates created (UNIQUE constraints working)

4. **Success Criteria**:
   - ✅ At least 5 items parsed from feed
   - ✅ No syntax/parsing errors in logs
   - ✅ Database constraints prevent duplicates

---

### Scenario 2: Website Scraping
**Purpose**: Verify that web pages can be scraped as content sources

1. **Setup**:
   - Add a public website as source (e.g., news site)
   - Select "website" type

2. **Execution**:
   - Trigger parse via scheduler or manual task

3. **Verification**:
   - Check source_items table has entry with website content
   - Verify title extracted from `<title>` tag
   - Verify content extracted from main article/content div

4. **Success Criteria**:
   - ✅ Title populated
   - ✅ Description/content extracted
   - ✅ No parsing errors

---

### Scenario 3: Post Creation from Parsed Content
**Purpose**: Verify that posts are created from parsed source items

1. **Setup**:
   - Complete Scenario 1 or 2 (have items in source_items)

2. **Execution**:
   - Via bot UI: `/create_post` → select source item → create post
   - OR via API: POST /api/posts with source_item_id

3. **Verification**:
   - Check `posts` table has new entry
   - Verify `title`, `body`, `source_item_id` are set
   - Verify `status` is "draft"

4. **Success Criteria**:
   - ✅ Post created successfully
   - ✅ All required fields populated
   - ✅ Status is "draft"

---

### Scenario 4: AI Content Rewriting
**Purpose**: Verify AI rewriting functionality

1. **Setup**:
   - Have a draft post from Scenario 3
   - Configure AI provider in .env (OpenAI or Anthropic)

2. **Execution**:
   - Via bot: `/ai_rewrite` → select post → select style (neutral/engaging/professional)
   - Wait for AI processing

3. **Verification**:
   - Check post has `rewrite_original` and `rewrite_candidate` populated
   - Verify rewritten content differs from original
   - Verify style preference is followed

4. **Success Criteria**:
   - ✅ AI rewrite completes without timeout (< 30s)
   - ✅ Content is rewritten
   - ✅ Can apply rewritten version to post

---

### Scenario 5: Post Publishing to Telegram
**Purpose**: Verify that posts can be published to Telegram channels

1. **Setup**:
   - Have a draft post
   - Have a Telegram channel added in bot
   - Channel must have bot as administrator

2. **Execution**:
   - Via bot: `/publish` → select post → select channel → confirm

3. **Verification**:
   - Check Telegram channel receives message
   - Verify message contains post title and body
   - Check `posts` table: status changed to "published", `published_at` set
   - Check logs for successful publish or retry attempts

4. **Success Criteria**:
   - ✅ Message appears in Telegram channel within 5 seconds
   - ✅ Message format is correct (HTML parsed, link included)
   - ✅ Database status updated
   - ✅ No errors in logs (or INFO level retry messages only)

---

### Scenario 6: Scheduled Publishing with Retry
**Purpose**: Verify scheduled publishing and retry mechanism

1. **Setup**:
   - Have a draft post
   - Channel where bot can't currently send (simulate failure)

2. **Execution**:
   - Via bot: Schedule post for 2 minutes from now
   - Monitor scheduler logs

3. **Verification**:
   - Check `publish_jobs` table: created with `status="pending"`, `scheduled_at` in future
   - After scheduled time: verify retry logic
   - Check exponential backoff delays are applied
   - After max retries: verify `status="failed"`, `error_message` recorded

4. **Success Criteria**:
   - ✅ Job scheduled correctly
   - ✅ Retries happen with increasing delays
   - ✅ Job marked failed after max retries
   - ✅ Error tracking works

---

### Scenario 7: FSM State Persistence
**Purpose**: Verify that FSM states survive bot restart

1. **Setup**:
   - Have bot running
   - Start `/create_post` flow, enter title
   - Stop bot (container)

2. **Execution**:
   - Wait 2 seconds
   - Restart bot container
   - Check bot responds to continue with content entry

3. **Verification**:
   - Check Redis has FSM state for user
   - Bot should allow continuing the flow

4. **Success Criteria**:
   - ✅ FSM state retrieved from Redis
   - ✅ Bot continues flow after restart
   - ✅ No "unknown command" error

---

### Scenario 8: Deduplication
**Purpose**: Verify that duplicate content is not created

1. **Setup**:
   - Parse same RSS feed twice or parse website twice

2. **Execution**:
   - First parse creates items
   - Second parse attempts same content

3. **Verification**:
   - Check source_items table
   - No new items created (UNIQUE(original_url) constraint)
   - OR if content_hash same: UNIQUE(source_id, content_hash) prevents duplicates

4. **Success Criteria**:
   - ✅ Duplicate check working
   - ✅ No extra rows created
   - ✅ Deduplication logged at DEBUG level

---

## Test Execution Checklist

- [ ] Docker compose stack started (`docker-compose up -d`)
- [ ] PostgreSQL initialized (run migrations)
- [ ] Redis running and accessible
- [ ] Bot token configured in .env
- [ ] API starts without errors
- [ ] Bot starts without errors

### Run Tests
- [ ] Scenario 1: RSS parsing ✓/✗
- [ ] Scenario 2: Website scraping ✓/✗
- [ ] Scenario 3: Post creation ✓/✗
- [ ] Scenario 4: AI rewriting ✓/✗
- [ ] Scenario 5: Publishing ✓/✗
- [ ] Scenario 6: Scheduled publishing with retry ✓/✗
- [ ] Scenario 7: FSM persistence ✓/✗
- [ ] Scenario 8: Deduplication ✓/✗

## Log Files to Monitor
- `docker-compose logs -f bot` - Bot logs
- `docker-compose logs -f api` - API logs
- `docker-compose logs -f worker` - Celery worker logs
- `docker-compose logs -f scheduler` - Scheduler logs

## Known Issues / Limitations
- Telegram API rate limiting may affect rapid test cycles
- AI processing requires valid API keys (test will fail gracefully if not configured)
- Some scenarios require manual Telegram channel setup (needs bot admin access)

## Next Steps After E2E Validation
1. Code review for security (IDOR, SSRF, injection)
2. Add integration tests to CI/CD
3. Performance testing with realistic load
4. Monitoring/alerting setup

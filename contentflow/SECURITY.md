# Security Guidelines for ContentFlow Bot

## 🔒 Security Fixes Implemented

### 1. Authorization (IDOR Prevention)

**Issue**: User ID was accepted from request parameters, allowing users to access/modify other users' resources.

**Fix**:
- All API endpoints now require JWT authentication via `get_current_user` dependency
- User ID is derived from the JWT token, not from request parameters
- Per-resource endpoints verify ownership: `if post.user_id != current_user.id: raise Forbidden`
- Applied to: sources, posts, channels endpoints

**Example**:
```python
@router.get("/")
async def list_posts(
    current_user: User = Depends(get_current_user),  # ✅ Secure
    db: AsyncSession = Depends(get_db),
):
    """User_id is derived from token, not from request"""
    query = select(Post).where(Post.user_id == current_user.id)
```

### 2. Mass Assignment Prevention

**Issue**: `setattr()` on all fields allowed attackers to modify sensitive fields like `user_id` and `bot_token`.

**Fix**:
- Created `ChannelUpdate` Pydantic model with explicit whitelist of editable fields
- Only `name`, `enabled`, and `username` can be edited by users
- Sensitive fields like `bot_token` and `telegram_id` are read-only
- Applied to: channels endpoint

**Example**:
```python
class ChannelUpdate(BaseModel):
    """Whitelist only user-editable fields"""
    name: Optional[str] = None
    enabled: Optional[bool] = None
    username: Optional[str] = None
    # bot_token, user_id, telegram_id are NOT editable

@router.patch("/{channel_id}")
async def update_channel(...):
    update_data = updates.dict(exclude_unset=True)
    # Only whitelisted fields are updated
```

### 3. SSRF Prevention

**Issue**: Parser could fetch URLs from private/internal networks, allowing attackers to scan internal infrastructure.

**Fix**:
- Added `_validate_url()` method that resolves hostname and checks IP address
- Rejects private IP ranges:
  - Loopback: 127.0.0.0/8, ::1
  - Link-local: 169.254.0.0/16
  - Private: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
  - Reserved: 0.0.0.0, 224.0.0.0/4, etc.
- Applied to: RSSParser and WebsiteParser

**Example**:
```python
class WebsiteParser(BaseParser):
    @staticmethod
    def _validate_url(url: str) -> bool:
        """Validate URL to prevent SSRF attacks"""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        
        hostname = parsed.hostname
        # Resolve and check IP
        ip_info = socket.getaddrinfo(hostname, 80, ...)
        for family, type_, proto, canonname, sockaddr in ip_info:
            ip = sockaddr[0]
            if is_private_ip(ip):
                logger.warning(f"SSRF attempt blocked for URL: {url}")
                return False
        return True
```

### 4. CORS Misconfiguration

**Issue**: `allow_origins=["*"]` with `allow_credentials=True` is a security misconfiguration that allows any origin to make authenticated requests.

**Fix**:
- Replaced wildcard `allow_origins` with explicit list of trusted origins
- Disabled `allow_credentials` for production (only credentials=False)
- Restricted `allow_methods` to: GET, POST, PUT, PATCH, DELETE
- Restricted `allow_headers` to: Content-Type, Authorization
- Configuration is environment-aware (development vs production)

**Example**:
```python
cors_origins = [
    "http://localhost:3000",      # Development
    "http://localhost:8080",
]

if not settings.debug:
    cors_origins = [
        "https://yourdomain.com",   # Production
        "https://www.yourdomain.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,    # ✅ Explicit whitelist
    allow_credentials=False,        # ✅ Disabled for security
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

## 🔐 Security Best Practices

### Environment Variables

**Store all secrets in environment variables:**
- `BOT_TOKEN` - Telegram bot token
- `DATABASE_URL` - Database credentials
- `REDIS_URL` - Redis credentials
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` - AI provider keys
- `SECRET_KEY` - JWT secret key

**Never commit secrets to git:**
```bash
# ✅ Good
cp .env.example .env
# Edit .env with real values (gitignored)

# ❌ Bad
git add .env  # Don't do this!
echo "API_KEY=sk-..." >> config.py  # Don't do this!
```

### API Authentication

**All endpoints require JWT token:**

```bash
# Get token (implement login endpoint)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": 123456789}'

# Use token
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/sources

# Response 401 if missing or invalid
```

### Input Validation

**Always validate user input:**
- Pydantic models validate request body
- URL validation prevents SSRF
- Rate limiting prevents abuse
- Database queries use parameterized statements (SQLAlchemy ORM)

### Database Security

**Configured safely by default:**
- Passwords hashed with bcrypt
- SQL injection prevention (ORM + parameterized queries)
- Connection pooling with SSL/TLS support
- Audit logging for sensitive operations

### Telegram Bot Security

**Token security:**
- Store `BOT_TOKEN` only in environment variables
- Never log or expose the token
- Use HTTPS webhooks if deployed (not polling)
- Validate telegram_id whitelist for admin users

**User validation:**
- Whitelist admin Telegram IDs in `ADMIN_TELEGRAM_IDS`
- Only admins can configure critical settings
- Log all admin actions

## 🛡️ Defense in Depth

### Layered Security

1. **Network Layer**
   - HTTPS/TLS for all external connections
   - Nginx reverse proxy with security headers
   - Firewall rules (ufw)

2. **Application Layer**
   - JWT authentication on all API endpoints
   - Authorization checks (user owns resource?)
   - Input validation (Pydantic models)
   - SSRF protection (hostname validation)
   - Rate limiting

3. **Data Layer**
   - PostgreSQL with strong credentials
   - Redis with password authentication
   - Encrypted connection strings
   - Regular backups

4. **Monitoring Layer**
   - Audit logs for all operations
   - Error logging with stack traces
   - Rate limit monitoring
   - Failed auth attempts logging

## 📋 Security Checklist

### Before Deployment

- [ ] All secrets in `.env` (not in code)
- [ ] Database credentials changed from defaults
- [ ] JWT `SECRET_KEY` is long and random
- [ ] CORS origins updated for production domain
- [ ] Redis password set (not localhost in production)
- [ ] SSL certificate installed (Let's Encrypt)
- [ ] Nginx configured with security headers
- [ ] Admin `TELEGRAM_IDS` configured
- [ ] Rate limiting enabled
- [ ] Logs configured and monitored

### Production Maintenance

- [ ] Regular security updates (dependencies)
- [ ] Database backups (daily)
- [ ] Log rotation (prevent disk full)
- [ ] Failed login monitoring
- [ ] SSRF/abuse pattern detection
- [ ] Dependency vulnerability scanning

## 🔄 Security Update Process

1. **Find vulnerability** → Create issue with `security` label
2. **Fix** → Patch immediately, test thoroughly
3. **Commit** → Include `security:` prefix in commit message
4. **Deploy** → Priority deployment to production
5. **Notify** → Inform users if they need to take action

## 📚 Further Reading

- [OWASP Top 10](https://owasp.org/Top10/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/sql-syntax.html#SQL-SYNTAX-LEXICAL-STRINGS-ESCAPE)
- [SQLAlchemy Security](https://docs.sqlalchemy.org/en/20/faq/security.html)

---

**Last Updated**: 2024-01-15  
**Security Level**: 🟢 High  
**Status**: ✅ All major vulnerabilities patched

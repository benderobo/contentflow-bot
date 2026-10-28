import hashlib
import hmac
import json
import os
import time
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from core.config import get_settings
from core.database import Base, get_db
from models.post import Post
from models.post_media import PostMedia
from models.user import User
from utils.media import MAX_IMAGE_SIZE, detect_image_type, resolve_media_path

settings = get_settings()

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 32


def init_data_for(telegram_id: int, bot_token: str = None, age: int = 0) -> str:
    """Build a correctly signed Telegram WebApp initData string."""
    bot_token = bot_token or settings.bot_token
    params = {
        "auth_date": str(int(time.time()) - age),
        "query_id": "AAA",
        "user": json.dumps({"id": telegram_id, "first_name": "T"}),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(params)


def auth(telegram_id: int, **kw) -> dict:
    return {"Authorization": f"tg-init-data {init_data_for(telegram_id, **kw)}"}


@pytest_asyncio.fixture
async def env(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/t.db", poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with maker() as session:
            yield session

    from api.main import app

    app.dependency_overrides[get_db] = override_get_db

    async with maker() as db:
        db.add_all([
            User(id=1, telegram_id=1001, is_active=True, is_approved=True),
            User(id=2, telegram_id=1002, is_active=True, is_approved=True),
        ])
        await db.flush()
        db.add(Post(id=10, user_id=1, title="t", body="b", status="draft"))
        db.add(Post(id=11, user_id=2, title="other", body="b", status="draft"))
        db.add(Post(id=12, user_id=1, title="done", body="b", status="published"))
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield SimpleNamespace(client=client, maker=maker)

    app.dependency_overrides.clear()
    await engine.dispose()


def up(content: bytes, name="pic.png", ctype="image/png"):
    return {"file": (name, content, ctype)}


# ---------- upload / list / download / delete ----------

@pytest.mark.asyncio
async def test_upload_list_download_delete_roundtrip(env):
    r = await env.client.post("/api/posts/10/media", files=up(PNG), headers=auth(1001))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["mime_type"] == "image/png"
    assert body["order"] == 0

    listed = await env.client.get("/api/posts/10/media", headers=auth(1001))
    assert [m["id"] for m in listed.json()] == [body["id"]]

    file_resp = await env.client.get(body["url"], headers=auth(1001))
    assert file_resp.status_code == 200
    assert file_resp.content == PNG
    assert file_resp.headers["content-type"] == "image/png"

    async with env.maker() as db:
        row = await db.get(PostMedia, body["id"])
        path = resolve_media_path(settings.media_storage_path, row.file_path)
        assert path.is_file()

    d = await env.client.delete(f"/api/posts/10/media/{body['id']}", headers=auth(1001))
    assert d.status_code == 204
    assert not path.exists()
    assert (await env.client.get("/api/posts/10/media", headers=auth(1001))).json() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("content,mime", [(JPEG, "image/jpeg"), (WEBP, "image/webp")])
async def test_accepts_jpeg_and_webp(env, content, mime):
    r = await env.client.post("/api/posts/10/media", files=up(content, "x.bin", "application/octet-stream"),
                              headers=auth(1001))
    assert r.status_code == 201
    assert r.json()["mime_type"] == mime


@pytest.mark.asyncio
async def test_order_increments(env):
    a = await env.client.post("/api/posts/10/media", files=up(PNG), headers=auth(1001))
    b = await env.client.post("/api/posts/10/media", files=up(JPEG, "b.jpg", "image/jpeg"), headers=auth(1001))
    assert (a.json()["order"], b.json()["order"]) == (0, 1)


# ---------- validation ----------

@pytest.mark.asyncio
async def test_rejects_non_image_with_fake_content_type(env):
    r = await env.client.post("/api/posts/10/media",
                              files=up(b"<html><script>alert(1)</script></html>", "evil.png", "image/png"),
                              headers=auth(1001))
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_rejects_gif(env):
    r = await env.client.post("/api/posts/10/media", files=up(b"GIF89a" + b"\x00" * 20, "a.gif", "image/gif"),
                              headers=auth(1001))
    assert r.status_code == 415


@pytest.mark.asyncio
async def test_rejects_empty_file(env):
    r = await env.client.post("/api/posts/10/media", files=up(b""), headers=auth(1001))
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_rejects_oversize(env):
    big = PNG + b"\x00" * MAX_IMAGE_SIZE
    r = await env.client.post("/api/posts/10/media", files=up(big), headers=auth(1001))
    assert r.status_code == 413


@pytest.mark.asyncio
async def test_rejects_duplicate(env):
    assert (await env.client.post("/api/posts/10/media", files=up(PNG), headers=auth(1001))).status_code == 201
    r = await env.client.post("/api/posts/10/media", files=up(PNG), headers=auth(1001))
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_limits_images_per_post(env):
    for i in range(10):
        r = await env.client.post("/api/posts/10/media", files=up(PNG + bytes([i]) * 4), headers=auth(1001))
        assert r.status_code == 201
    r = await env.client.post("/api/posts/10/media", files=up(PNG + b"\xff" * 4), headers=auth(1001))
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_published_post_is_locked(env):
    r = await env.client.post("/api/posts/12/media", files=up(PNG), headers=auth(1001))
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_original_filename_is_discarded(env):
    r = await env.client.post("/api/posts/10/media", files=up(PNG, "../../etc/passwd.png"), headers=auth(1001))
    assert r.status_code == 201
    async with env.maker() as db:
        row = await db.get(PostMedia, r.json()["id"])
        assert ".." not in row.file_path and "passwd" not in row.file_path
        assert row.file_path.startswith("10/") and row.file_path.endswith(".png")


# ---------- auth / ownership ----------

@pytest.mark.asyncio
async def test_requires_auth(env):
    assert (await env.client.post("/api/posts/10/media", files=up(PNG))).status_code == 401
    assert (await env.client.get("/api/posts/10/media")).status_code == 401


@pytest.mark.asyncio
async def test_rejects_forged_and_expired_init_data(env):
    forged = auth(1001, bot_token="999:OTHER")
    assert (await env.client.post("/api/posts/10/media", files=up(PNG), headers=forged)).status_code == 401
    expired = auth(1001, age=2 * 86400)
    assert (await env.client.post("/api/posts/10/media", files=up(PNG), headers=expired)).status_code == 401


@pytest.mark.asyncio
async def test_unknown_telegram_user_rejected(env):
    r = await env.client.get("/api/posts/10/media", headers=auth(555555))
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_cannot_touch_someone_elses_post(env):
    r = await env.client.post("/api/posts/11/media", files=up(PNG), headers=auth(1001))
    assert r.status_code == 403
    mine = await env.client.post("/api/posts/10/media", files=up(PNG), headers=auth(1001))
    # user 2 can neither read, download nor delete user 1's media
    other = auth(1002)
    assert (await env.client.get("/api/posts/10/media", headers=other)).status_code == 403
    assert (await env.client.get(mine.json()["url"], headers=other)).status_code == 403
    assert (await env.client.delete(f"/api/posts/10/media/{mine.json()['id']}", headers=other)).status_code == 403


@pytest.mark.asyncio
async def test_media_id_must_belong_to_post(env):
    async with env.maker() as db:
        db.add(Post(id=13, user_id=1, title="x", body="y", status="draft"))
        await db.commit()
    m = await env.client.post("/api/posts/10/media", files=up(PNG), headers=auth(1001))
    r = await env.client.get(f"/api/posts/13/media/{m.json()['id']}/file", headers=auth(1001))
    assert r.status_code == 404


# ---------- miniapp post endpoints ----------

@pytest.mark.asyncio
async def test_miniapp_can_create_get_and_update_post(env):
    c = await env.client.post("/api/posts/", json={"title": "T", "body": "B", "hashtags": ["#a"]},
                              headers=auth(1001))
    assert c.status_code == 200, c.text
    pid = c.json()["id"]

    g = await env.client.get(f"/api/posts/{pid}", headers=auth(1001))
    assert g.status_code == 200 and g.json()["title"] == "T" and g.json()["hashtags"] == ["#a"]

    u = await env.client.patch(f"/api/posts/{pid}", json={"title": "T2"}, headers=auth(1001))
    assert u.status_code == 200 and u.json()["title"] == "T2"

    assert (await env.client.get(f"/api/posts/{pid}", headers=auth(1002))).status_code == 403
    assert (await env.client.get("/api/posts/999", headers=auth(1001))).status_code == 404


# ---------- helpers ----------

def test_detect_image_type():
    assert detect_image_type(PNG) == ("png", "image/png")
    assert detect_image_type(JPEG) == ("jpg", "image/jpeg")
    assert detect_image_type(WEBP) == ("webp", "image/webp")
    assert detect_image_type(b"RIFF\x00\x00\x00\x00WAVE") is None
    assert detect_image_type(b"") is None


def test_resolve_media_path_blocks_traversal(tmp_path):
    root = str(tmp_path)
    assert resolve_media_path(root, "1/a.png") == (tmp_path / "1" / "a.png").resolve()
    for bad in ["../x.png", "1/../../x.png", "/etc/passwd"]:
        with pytest.raises(ValueError):
            resolve_media_path(root, bad)


# ---------- publishing ----------

class FakeBot:
    def __init__(self):
        self.calls = []

    async def send_message(self, **kw):
        self.calls.append(("message", kw))

    async def send_photo(self, **kw):
        self.calls.append(("photo", kw))

    async def send_media_group(self, **kw):
        self.calls.append(("group", kw))


async def _attach(env, n):
    for i in range(n):
        r = await env.client.post("/api/posts/10/media", files=up(PNG + bytes([i]) * 4), headers=auth(1001))
        assert r.status_code == 201


@pytest.mark.asyncio
async def test_publish_without_images_sends_text_only(env):
    from workers.tasks import _send_post_to_channel
    bot = FakeBot()
    async with env.maker() as db:
        await _send_post_to_channel(db, bot, "@ch", 10, "hello")
    assert [c[0] for c in bot.calls] == ["message"]


@pytest.mark.asyncio
async def test_publish_single_image_uses_caption(env):
    from workers.tasks import _send_post_to_channel
    await _attach(env, 1)
    bot = FakeBot()
    async with env.maker() as db:
        await _send_post_to_channel(db, bot, "@ch", 10, "short text")
    assert [c[0] for c in bot.calls] == ["photo"]
    assert bot.calls[0][1]["caption"] == "short text"


@pytest.mark.asyncio
async def test_publish_album_puts_caption_on_first_only(env):
    from workers.tasks import _send_post_to_channel
    await _attach(env, 3)
    bot = FakeBot()
    async with env.maker() as db:
        await _send_post_to_channel(db, bot, "@ch", 10, "short text")
    assert [c[0] for c in bot.calls] == ["group"]
    media = bot.calls[0][1]["media"]
    assert len(media) == 3
    assert media[0].caption == "short text" and media[1].caption is None


@pytest.mark.asyncio
async def test_publish_long_text_is_sent_separately(env):
    from workers.tasks import _send_post_to_channel
    await _attach(env, 2)
    bot = FakeBot()
    long_text = "x" * 1500
    async with env.maker() as db:
        await _send_post_to_channel(db, bot, "@ch", 10, long_text)
    assert [c[0] for c in bot.calls] == ["group", "message"]
    assert all(m.caption is None for m in bot.calls[0][1]["media"])
    assert bot.calls[1][1]["text"] == long_text


@pytest.mark.asyncio
async def test_publish_skips_missing_files(env):
    from workers.tasks import _send_post_to_channel
    await _attach(env, 1)
    async with env.maker() as db:
        row = (await db.execute(PostMedia.__table__.select())).first()
        os.remove(resolve_media_path(settings.media_storage_path, row.file_path))
        bot = FakeBot()
        await _send_post_to_channel(db, bot, "@ch", 10, "text")
    assert [c[0] for c in bot.calls] == ["message"]

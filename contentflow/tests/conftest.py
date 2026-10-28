"""Test environment: must run before any contentflow module reads settings."""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="contentflow-tests-")

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN_FOR_TESTS_ONLY")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TMP}/unused.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("API_KEY", "test-api-key")
os.environ["MEDIA_STORAGE_PATH"] = os.path.join(_TMP, "media")

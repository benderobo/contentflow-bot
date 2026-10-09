import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from core.config import get_settings
from core.database import init_db, close_db, get_db
from api.routes import sources, posts, channels, ai, stats, users

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="ContentFlow API",
    description="API for ContentFlow Bot - Content Management System for Telegram",
    version="1.0.0",
)

# Add CORS middleware (restricted to specific origins)
cors_origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "https://localhost:3000",
]

# In production, add your domain
if not settings.debug:
    cors_origins = [
        "https://yourdomain.com",
        "https://www.yourdomain.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,  # Disable credentials for wildcard CORS safety
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await init_db()
    logger.info("API startup complete")


@app.on_event("shutdown")
async def shutdown():
    """Close database on shutdown."""
    await close_db()
    logger.info("API shutdown complete")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ContentFlow API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Include routers
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])
app.include_router(channels.router, prefix="/api/channels", tags=["channels"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])


# Serve web app from ../web/build. Must be registered after the API routers.
# A single Mount handles /app, /app/ and /app?post_id=... (an explicit
# @app.get("/app") route would shadow the mount for the bot's URLs).
web_build_path = os.path.join(os.path.dirname(__file__), "..", "web", "build")
if os.path.isdir(web_build_path) and os.listdir(web_build_path):
    app.mount("/app", StaticFiles(directory=web_build_path, html=True), name="web")
    logger.info(f"Mounted web app at /app from {web_build_path}")
else:
    logger.warning(f"Web app build not found at {web_build_path}, serving placeholder")

    @app.get("/app")
    async def serve_app_placeholder():
        """Fallback when the React build is missing."""
        return HTMLResponse("<h1>📝 ContentFlow Editor</h1><p>Веб-редактор для постов</p>")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )

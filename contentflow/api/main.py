import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from core.config import get_settings
from core.database import init_db, close_db, get_db
from api.routes import sources, posts, channels, ai, stats

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="ContentFlow API",
    description="API for ContentFlow Bot - Content Management System for Telegram",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])
app.include_router(channels.router, prefix="/api/channels", tags=["channels"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )

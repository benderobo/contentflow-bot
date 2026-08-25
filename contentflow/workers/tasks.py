import logging
import asyncio
from celery import Celery
from sqlalchemy import select
from datetime import datetime

from core.config import get_settings
from core.database import AsyncSessionLocal, Base, engine
from models.source import Source
from models.source_item import SourceItem
from models.post import Post
from services.parser import ParserFactory
from services.deduplication import DeduplicationService
from services.ai import AIService

settings = get_settings()

celery_app = Celery(
    "contentflow",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

logger = logging.getLogger(__name__)


@celery_app.task(name="parse_source")
def parse_source(source_id: int):
    """Parse content from a source."""
    asyncio.run(_parse_source_async(source_id))


async def _parse_source_async(source_id: int):
    """Async implementation of source parsing."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Source).where(Source.id == source_id))
        source = result.scalar_one_or_none()

        if not source or not source.enabled:
            return

        try:
            parser = ParserFactory.get_parser(source.type)
            if not parser:
                logger.warning(f"No parser for type: {source.type}")
                return

            items = await parser.parse(source.parser_config)
            source.last_check = datetime.utcnow()

            for item in items:
                # Check if URL already exists
                url_result = await db.execute(
                    select(SourceItem).where(SourceItem.original_url == item.get("url"))
                )
                existing = url_result.scalar_one_or_none()

                if existing:
                    logger.info(f"Item already exists: {item.get('url')}")
                    continue

                # Create new source item
                content_hash = DeduplicationService.hash_content(
                    item.get("description", "")
                )
                source_item = SourceItem(
                    source_id=source.id,
                    original_url=item.get("url", ""),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    content_hash=content_hash,
                    author=item.get("author"),
                    published_at=item.get("published_at"),
                )
                db.add(source_item)

            source.last_success = datetime.utcnow()
            source.error_count = 0
            db.add(source)
            await db.commit()

            logger.info(f"Parsed {len(items)} items from source {source_id}")
        except Exception as e:
            logger.error(f"Error parsing source {source_id}: {e}")
            source.last_error = str(e)
            source.error_count += 1
            db.add(source)
            await db.commit()


@celery_app.task(name="analyze_content")
def analyze_content(source_item_id: int):
    """Analyze content with AI."""
    asyncio.run(_analyze_content_async(source_item_id))


async def _analyze_content_async(source_item_id: int):
    """Async implementation of content analysis."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SourceItem).where(SourceItem.id == source_item_id))
        item = result.scalar_one_or_none()

        if not item:
            return

        try:
            # TODO: Initialize AI service with user's provider
            logger.info(f"Analyzing content {source_item_id}")

            # TODO: Implement AI analysis
            # analysis = await ai_service.analyze_content(item.description)

            # Create post from analyzed content
            post = Post(
                user_id=1,  # TODO: Get from source owner
                source_item_id=item.id,
                original_url=item.original_url,
                title=item.title,
                body=item.description,
                status="draft",
            )
            db.add(post)
            await db.commit()
        except Exception as e:
            logger.error(f"Error analyzing content {source_item_id}: {e}")


@celery_app.task(name="publish_post")
def publish_post(post_id: int, channel_id: int):
    """Publish a post to a Telegram channel."""
    asyncio.run(_publish_post_async(post_id, channel_id))


async def _publish_post_async(post_id: int, channel_id: int):
    """Async implementation of post publishing."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()

        if not post:
            return

        try:
            # TODO: Implement Telegram publishing
            post.status = "published"
            post.published_at = datetime.utcnow()
            db.add(post)
            await db.commit()
            logger.info(f"Published post {post_id} to channel {channel_id}")
        except Exception as e:
            logger.error(f"Error publishing post {post_id}: {e}")

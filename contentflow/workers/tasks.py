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

            # Build parser config with URL
            parser_config = source.parser_config.copy() if source.parser_config else {}
            parser_config["url"] = source.url

            items = await parser.parse(parser_config)
            source.last_check = datetime.utcnow()

            saved_count = 0
            for item in items:
                # Check if URL already exists
                url_result = await db.execute(
                    select(SourceItem).where(SourceItem.original_url == item.get("url"))
                )
                existing = url_result.scalar_one_or_none()

                if existing:
                    logger.debug(f"Item already exists: {item.get('url')}")
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
                saved_count += 1

            source.last_success = datetime.utcnow()
            source.error_count = 0
            db.add(source)
            await db.commit()

            logger.info(f"Parsed {len(items)} items, saved {saved_count} new items from source {source_id}")
        except Exception as e:
            logger.error(f"Error parsing source {source_id}: {e}")
            source.last_error = str(e)[:1000]
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
            from services.ai import AIService, OpenAIProvider
            from models.source import Source

            # Get source to find user
            source_result = await db.execute(select(Source).where(Source.id == item.source_id))
            source = source_result.scalar_one_or_none()

            if not source:
                return

            # Initialize AI service if configured
            if settings.openai_api_key:
                ai_provider = OpenAIProvider(settings.openai_api_key, settings.ai_model)
                ai_service = AIService(ai_provider)
                analysis = await ai_service.analyze_content(item.description or item.title or "")
            else:
                analysis = {"relevant": True, "importance": 5}

            # Update source item with analysis
            item.ai_analysis = analysis
            db.add(item)

            # Create post from analyzed content if relevant
            if analysis.get("relevant", True):
                post = Post(
                    user_id=source.user_id,
                    source_item_id=item.id,
                    original_url=item.original_url,
                    title=item.title,
                    body=item.description or item.title,
                    status="draft",
                    ai_analysis=analysis,
                    category=analysis.get("category"),
                    importance=analysis.get("importance", 5),
                    clickbait=analysis.get("clickbait", False),
                )
                db.add(post)

            await db.commit()
            logger.info(f"Analyzed content {source_item_id}, importance: {analysis.get('importance', 5)}")
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

        # Get channel info
        from models.channel import Channel
        channel_result = await db.execute(select(Channel).where(Channel.id == channel_id))
        channel = channel_result.scalar_one_or_none()

        if not channel:
            logger.error(f"Channel {channel_id} not found")
            return

        try:
            from aiogram import Bot

            # Send message to Telegram channel
            bot = Bot(token=settings.bot_token)

            # Format post message
            message_text = f"📝 <b>{post.title}</b>\n\n"
            message_text += post.body

            if post.original_url:
                message_text += f"\n\n🔗 <a href='{post.original_url}'>Источник</a>"

            # Send to channel
            await bot.send_message(
                chat_id=channel.telegram_id,
                text=message_text,
                parse_mode="HTML"
            )

            # Update post status
            post.status = "published"
            post.published_at = datetime.utcnow()
            db.add(post)

            # Update publish job
            from models.publish_job import PublishJob
            job_result = await db.execute(
                select(PublishJob).where(
                    PublishJob.post_id == post_id,
                    PublishJob.channel_id == channel_id,
                    PublishJob.status == "publishing"
                )
            )
            job = job_result.scalar_one_or_none()
            if job:
                job.status = "published"
                job.published_at = datetime.utcnow()
                db.add(job)

            await db.commit()
            logger.info(f"Published post {post_id} to channel {channel_id} ({channel.name})")
        except Exception as e:
            logger.error(f"Error publishing post {post_id}: {e}")

            # Update job with error
            from models.publish_job import PublishJob
            job_result = await db.execute(
                select(PublishJob).where(
                    PublishJob.post_id == post_id,
                    PublishJob.channel_id == channel_id,
                    PublishJob.status == "publishing"
                )
            )
            job = job_result.scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                job.retry_count += 1

                # Retry if not exceeded max retries
                if job.retry_count < job.max_retries:
                    job.status = "pending"
                    logger.info(f"Retrying publish job {job.id} (attempt {job.retry_count})")

                db.add(job)
                await db.commit()

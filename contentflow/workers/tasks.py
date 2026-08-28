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

            saved_items = []
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
                await db.flush()  # Get the ID immediately

                # Create post immediately (don't wait for analyze_content)
                post = Post(
                    user_id=source.user_id,
                    source_item_id=source_item.id,
                    original_url=item.get("url", ""),
                    title=item.get("title", ""),
                    body=item.get("description", ""),
                    status="draft",
                    category="general",
                    importance=5,
                )
                db.add(post)
                saved_items.append(source_item.id)
                saved_count += 1

            source.last_success = datetime.utcnow()
            source.error_count = 0
            db.add(source)
            await db.commit()

            logger.info(f"Parsed {len(items)} items, saved {saved_count} new posts from source {source_id}")

            # Queue analysis for newly created items
            for item_id in saved_items:
                analyze_content.delay(item_id)
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

            # Update existing post with analysis (post already created by parse_source)
            post_result = await db.execute(
                select(Post).where(Post.source_item_id == item.id)
            )
            post = post_result.scalar_one_or_none()

            if post:
                post.ai_analysis = analysis
                post.category = analysis.get("category", "general")
                post.importance = analysis.get("importance", 5)
                post.clickbait = analysis.get("clickbait", False)

                # Mark as irrelevant if AI says so
                if not analysis.get("relevant", True):
                    post.status = "irrelevant"

                db.add(post)

            await db.commit()
            logger.info(f"Analyzed content {source_item_id}, importance: {analysis.get('importance', 5)}")
        except Exception as e:
            logger.error(f"Error analyzing content {source_item_id}: {e}")


@celery_app.task(name="publish_post", bind=True, autoretry_for=(Exception,), max_retries=5)
def publish_post(self, post_id: int, channel_id: int):
    """Publish a post to a Telegram channel."""
    asyncio.run(_publish_post_async(post_id, channel_id, self.request.retries))


async def _publish_post_async(post_id: int, channel_id: int, retry_attempt: int = 0):
    """Async implementation of post publishing with retry support."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Post).where(Post.id == post_id))
        post = result.scalar_one_or_none()

        if not post:
            logger.error(f"Post {post_id} not found")
            return

        from models.channel import Channel
        channel_result = await db.execute(select(Channel).where(Channel.id == channel_id))
        channel = channel_result.scalar_one_or_none()

        if not channel:
            logger.error(f"Channel {channel_id} not found")
            return

        try:
            from services.telegram_bot import get_bot, is_retryable_error
            from aiogram.exceptions import TelegramAPIError

            bot = get_bot()

            message_text = f"📝 <b>{post.title}</b>\n\n"
            message_text += post.body

            if post.original_url:
                message_text += f"\n\n🔗 <a href='{post.original_url}'>Источник</a>"

            await bot.send_message(
                chat_id=channel.telegram_id,
                text=message_text,
                parse_mode="HTML"
            )

            post.status = "published"
            post.published_at = datetime.utcnow()
            db.add(post)

            from models.publish_job import PublishJob
            job_result = await db.execute(
                select(PublishJob).where(
                    PublishJob.post_id == post_id,
                    PublishJob.channel_id == channel_id
                )
            )
            job = job_result.scalar_one_or_none()
            if job:
                job.status = "published"
                job.published_at = datetime.utcnow()
                job.retry_count = retry_attempt
                db.add(job)

            await db.commit()
            logger.info(f"Published post {post_id} to channel {channel_id} ({channel.name})")

        except Exception as e:
            logger.error(f"Error publishing post {post_id} (attempt {retry_attempt + 1}): {e}")

            from models.publish_job import PublishJob
            job_result = await db.execute(
                select(PublishJob).where(
                    PublishJob.post_id == post_id,
                    PublishJob.channel_id == channel_id
                )
            )
            job = job_result.scalar_one_or_none()

            if job:
                job.retry_count = retry_attempt + 1
                job.error_message = str(e)[:500]

                from services.telegram_bot import is_retryable_error
                if is_retryable_error(e) and job.retry_count < job.max_retries:
                    job.status = "pending"
                    logger.info(f"Scheduling retry for publish job {job.id} (attempt {job.retry_count})")
                    from services.telegram_bot import get_retry_delay
                    delay = get_retry_delay(job.retry_count - 1)
                    job.scheduled_at = datetime.utcnow() + __import__('datetime').timedelta(seconds=delay)
                else:
                    job.status = "failed"
                    logger.error(f"Publish job {job.id} failed permanently after {job.retry_count} attempts")

                db.add(job)
                await db.commit()

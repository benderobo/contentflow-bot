import asyncio
import logging
from datetime import datetime
from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.publish_job import PublishJob
from models.source import Source
from models.source_item import SourceItem
from workers.tasks import publish_post, parse_source, analyze_content

logger = logging.getLogger(__name__)


async def run_scheduler():
    """Main scheduler loop to check and publish scheduled posts, and parse sources."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                # Find all pending jobs that are due
                result = await db.execute(
                    select(PublishJob).where(
                        PublishJob.status.in_(["pending", "failed"]),
                        PublishJob.scheduled_at <= datetime.utcnow(),
                        PublishJob.retry_count < PublishJob.max_retries
                    )
                )
                pending_jobs = result.scalars().all()

                for job in pending_jobs:
                    # Queue the publish task
                    publish_post.delay(job.post_id, job.channel_id)
                    logger.info(f"Queued publish job {job.id} for post {job.post_id} to channel {job.channel_id}")

                    job.status = "publishing"
                    job.updated_at = datetime.utcnow()
                    db.add(job)

                # Find sources that need parsing
                result = await db.execute(
                    select(Source).where(Source.enabled == True)
                )
                sources = result.scalars().all()

                for source in sources:
                    should_parse = False

                    # Check if source has never been parsed
                    if source.last_check is None:
                        should_parse = True
                    else:
                        # Check if enough time has passed since last check
                        elapsed = (datetime.utcnow() - source.last_check).total_seconds()
                        if elapsed >= source.parse_interval:
                            should_parse = True

                    if should_parse:
                        parse_source.delay(source.id)
                        logger.info(f"Queued parse task for source {source.id} ({source.name})")

                # Find source items without analysis
                result = await db.execute(
                    select(SourceItem).where(
                        SourceItem.ai_analysis == None
                    ).limit(10)
                )
                unanalyzed = result.scalars().all()

                for item in unanalyzed:
                    analyze_content.delay(item.id)
                    logger.info(f"Queued analysis for source item {item.id}")

                await db.commit()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        # Check every 60 seconds
        await asyncio.sleep(60)


async def main():
    """Start the scheduler."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting publish scheduler")
    await run_scheduler()


if __name__ == "__main__":
    asyncio.run(main())

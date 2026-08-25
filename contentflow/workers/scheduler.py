import asyncio
import logging
from datetime import datetime
from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.publish_job import PublishJob
from workers.tasks import publish_post

logger = logging.getLogger(__name__)


async def run_scheduler():
    """Main scheduler loop to check and publish scheduled posts."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                # Find all pending jobs that are due
                result = await db.execute(
                    select(PublishJob).where(
                        PublishJob.status == "pending",
                        PublishJob.scheduled_at <= datetime.utcnow(),
                    )
                )
                pending_jobs = result.scalars().all()

                for job in pending_jobs:
                    # Queue the publish task
                    publish_post.delay(job.post_id, job.channel_id)
                    logger.info(f"Queued publish job {job.id} for post {job.post_id}")

                    job.status = "publishing"
                    db.add(job)

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

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.pipelines.etl import run_pipeline

logger = logging.getLogger(__name__)


def start_scheduler():
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(hour=6, minute=0),
        id="daily_pipeline",
        name="Daily ETL Pipeline",
        replace_existing=True,
    )

    scheduler.start()

    logger.info(
        "Scheduler started — pipeline will run daily at 06:00 AM"
    )

    return scheduler
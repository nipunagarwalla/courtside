"""APScheduler setup for recurring background jobs."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import AsyncSessionLocal
from scrapers.atp_rankings import scrape_atp_rankings
from scrapers.ibm.poller import check_live_matches

scheduler = AsyncIOScheduler(timezone="UTC")


async def scrape_atp_rankings_job():
    async with AsyncSessionLocal() as db:
        await scrape_atp_rankings(db)


def start_scheduler():
    scheduler.add_job(
        scrape_atp_rankings_job,
        CronTrigger(day_of_week="mon", hour=6, minute=0),
        id="atp_rankings_weekly",
        replace_existing=True,
    )
    scheduler.add_job(
        check_live_matches,
        "interval",
        minutes=5,
        id="check_live_matches",
        replace_existing=True,
    )
    scheduler.start()
    for job in scheduler.get_jobs():
        print(f"Scheduler: registered job '{job.id}', next run {job.next_run_time}")


def stop_scheduler():
    scheduler.shutdown(wait=False)

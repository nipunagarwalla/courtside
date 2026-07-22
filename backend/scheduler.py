"""APScheduler setup for recurring background jobs."""
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import AsyncSessionLocal
from scrapers.atp_rankings import scrape_atp_rankings, scrape_ranking_points
from scrapers.atp_schedule import scrape_atp_calendar
from scrapers.atp_live import refresh_atp_live
from scrapers.ibm.poller import check_live_matches

scheduler = AsyncIOScheduler(timezone="UTC")


async def scrape_atp_rankings_job():
    async with AsyncSessionLocal() as db:
        await scrape_ranking_points(db)  # authoritative rank + points
        await scrape_atp_rankings(db)    # per-player enrichment


async def refresh_calendar_job():
    async with AsyncSessionLocal() as db:
        await scrape_atp_calendar(db)


def make_monthly_retrain_job(app):
    async def run_monthly_retrain():
        import asyncio
        import sys

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "ml.train",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        print("Retrain output:", stdout.decode()[-500:])
        if proc.returncode == 0 and app is not None:
            from ml.predict import MatchPredictor
            app.state.predictor = MatchPredictor()
            print("Predictor reloaded after retrain")

    return run_monthly_retrain


def start_scheduler(app=None):
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
    scheduler.add_job(
        refresh_atp_live,
        "interval",
        minutes=5,
        id="refresh_atp_live",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),  # populate immediately on startup
    )
    scheduler.add_job(
        refresh_calendar_job,
        CronTrigger(hour=3, minute=30),
        id="refresh_atp_calendar",
        replace_existing=True,
    )
    scheduler.add_job(
        make_monthly_retrain_job(app),
        CronTrigger(day=1, hour=2, minute=0),
        id="ml_monthly_retrain",
        replace_existing=True,
    )
    scheduler.start()
    for job in scheduler.get_jobs():
        print(f"Scheduler: registered job '{job.id}', next run {job.next_run_time}")


def stop_scheduler():
    scheduler.shutdown(wait=False)

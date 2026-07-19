"""Fetch current ATP ranks + enrich player profiles via the ATP hero API.

Usage (from backend/):
    python -m scrapers.atp_rankings            # players active in the last year
    python -m scrapers.atp_rankings --all      # every player in the table
    python -m scrapers.atp_rankings --limit 20 # quick smoke test

The players.id column holds the 4-character ATP player ID (e.g. "S0AG"),
loaded from TennisMyLife, and is used directly in the hero API URL.
"""
import argparse
import asyncio
import time
from datetime import date, datetime

import requests
from sqlalchemy import text

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.atptour.com/",
    "Accept": "application/json",
}

REQUEST_DELAY_S = 0.5  # be polite — 0.5s between requests

_session = requests.Session()
_session.headers.update(HEADERS)


def fetch_player_hero(atp_id: str, retries: int = 2) -> dict | None:
    """Fetch one player's hero JSON. Returns None on failure or unknown ID.

    Cloudflare occasionally serves a transient challenge page; a short
    backoff + retry recovers it.
    """
    url = f"https://www.atptour.com/en/-/www/players/hero/{atp_id}?v=1"
    for attempt in range(retries + 1):
        try:
            r = _session.get(url, timeout=15)
            if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
                return r.json()  # can be None: API returns `null` for unknown IDs
        except Exception as e:
            print(f"  Error fetching {atp_id}: {e}")
        if attempt < retries:
            time.sleep(2 * (attempt + 1))
    return None


def _to_date(iso_ts):
    if not iso_ts:
        return None
    try:
        return datetime.fromisoformat(iso_ts).date()
    except (TypeError, ValueError):
        return None


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


UPSERT_RANKING = text("""
    INSERT INTO rankings (player_id, tour, rank, points, ranking_type, week_date)
    VALUES (:player_id, :tour, :rank, :points, :ranking_type, :week_date)
    ON CONFLICT (player_id, week_date, ranking_type)
    DO UPDATE SET rank = EXCLUDED.rank
""")

UPDATE_PLAYER = text("""
    UPDATE players SET
        coach = :coach,
        height_cm = COALESCE(:height_cm, height_cm),
        weight_kg = :weight_kg,
        hi_rank = :hi_rank,
        hi_rank_date = :hi_rank_date,
        career_wins = :career_wins,
        career_losses = :career_losses,
        career_titles = :career_titles,
        ytd_wins = :ytd_wins,
        ytd_losses = :ytd_losses,
        ytd_titles = :ytd_titles,
        career_prize = :career_prize
    WHERE id = :id
""")


async def get_players(db, active_within_days: int | None, limit: int | None):
    where = ""
    if active_within_days is not None:
        where = f"""
            WHERE p.id IN (
                SELECT winner_id FROM matches WHERE match_date >= CURRENT_DATE - {int(active_within_days)}
                UNION
                SELECT loser_id FROM matches WHERE match_date >= CURRENT_DATE - {int(active_within_days)}
            )
        """
    sql = f"SELECT p.id, p.name FROM players p {where} ORDER BY p.name"
    if limit:
        sql += f" LIMIT {int(limit)}"
    result = await db.execute(text(sql))
    return result.all()


async def scrape_atp_rankings(db, active_within_days: int | None = 365, limit: int | None = None):
    """Fetch current rank + enrich player data via the ATP hero API.

    By default only players with a match in the last `active_within_days`
    days are scraped (the hero API has nothing useful for long-retired
    players); pass active_within_days=None for everyone.
    """
    players = await get_players(db, active_within_days, limit)
    today = date.today()
    updated = 0
    print(f"Scraping ATP hero API for {len(players)} players "
          f"(delay {REQUEST_DELAY_S}s between requests)")

    for player in players:
        data = await asyncio.to_thread(fetch_player_hero, player.id)
        if data:
            rank = _to_int(data.get("SglRank"))
            if rank:
                await db.execute(UPSERT_RANKING, {
                    "player_id": player.id,
                    "tour": "atp",
                    "rank": rank,
                    "points": None,  # points not in hero API
                    "ranking_type": "standard",
                    "week_date": today,
                })

            await db.execute(UPDATE_PLAYER, {
                "id": player.id,
                "coach": data.get("Coach"),
                "height_cm": _to_int(data.get("HeightCm")),
                "weight_kg": _to_int(data.get("WeightKg")),
                "hi_rank": _to_int(data.get("SglHiRank")),
                "hi_rank_date": _to_date(data.get("SglHiRankDate")),
                "career_wins": _to_int(data.get("SglCareerWon")),
                "career_losses": _to_int(data.get("SglCareerLost")),
                "career_titles": _to_int(data.get("SglCareerTitles")),
                "ytd_wins": _to_int(data.get("SglYtdWon")),
                "ytd_losses": _to_int(data.get("SglYtdLost")),
                "ytd_titles": _to_int(data.get("SglYtdTitles")),
                "career_prize": data.get("CareerPrizeFormatted"),
            })
            await db.commit()
            updated += 1
            print(f"  [{time.strftime('%H:%M:%S')}] {player.name}: rank {rank}")
        else:
            print(f"  [{time.strftime('%H:%M:%S')}] {player.name} ({player.id}): no hero data")

        await asyncio.sleep(REQUEST_DELAY_S)

    print(f"Updated {updated} players")
    return updated


async def _main():
    parser = argparse.ArgumentParser(description="Scrape ATP hero API")
    parser.add_argument("--all", action="store_true",
                        help="scrape every player, not just recently active ones")
    parser.add_argument("--days", type=int, default=365,
                        help="activity window in days (default 365)")
    parser.add_argument("--limit", type=int, default=None,
                        help="max players to scrape (for testing)")
    args = parser.parse_args()

    from database import AsyncSessionLocal, engine
    async with AsyncSessionLocal() as db:
        await scrape_atp_rankings(
            db,
            active_within_days=None if args.all else args.days,
            limit=args.limit,
        )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())

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
import re
import time
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup
from sqlalchemy import text

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.atptour.com/",
    "Accept": "application/json",
}

# The hero API (per-player enrichment) does NOT expose ranking points, so the
# authoritative rank+points come from the SSR'd rankings table page instead.
RANKINGS_URL = "https://www.atptour.com/en/rankings/singles?rankRange=1-2000"
RANKINGS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.atptour.com/",
    "Accept": "text/html,application/xhtml+xml",
}
_PLAYER_ID_RE = re.compile(r"/players/[^/]+/([a-z0-9]{3,4})/")

REQUEST_DELAY_S = 0.5  # be polite — 0.5s between requests

_session = requests.Session()
_session.headers.update(HEADERS)


UPSERT_RANK_POINTS = text("""
    INSERT INTO rankings (player_id, tour, rank, points, ranking_type, week_date)
    VALUES (:player_id, 'atp', :rank, :points, 'standard', :week_date)
    ON CONFLICT (player_id, week_date, ranking_type)
    DO UPDATE SET rank = EXCLUDED.rank, points = EXCLUDED.points
""")


def fetch_ranking_rows() -> list[tuple[int, str, int | None]]:
    """Scrape the ATP singles rankings page -> [(rank, player_id, points)].

    player_id is uppercased to match our DB convention. Deduped by id.
    """
    r = requests.get(RANKINGS_URL, headers=RANKINGS_HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # The page renders two rows per player (a desktop table and a wider mobile
    # table with extra columns), so select cells by CSS class rather than by
    # position — `td.rank` and `td.points` are correct in both variants.
    def cell_int(tr, cls):
        td = tr.select_one(f"td.{cls}")
        if not td:
            return None
        try:
            return int(td.get_text(strip=True).replace(",", ""))
        except ValueError:
            return None

    seen: dict[str, tuple[int, int | None]] = {}
    for tr in soup.select("tr"):
        link = tr.select_one('a[href*="/players/"]')
        if not link:
            continue
        m = _PLAYER_ID_RE.search(link.get("href", ""))
        if not m:
            continue
        rank = cell_int(tr, "rank")
        if rank is None:
            continue
        seen[m.group(1).upper()] = (rank, cell_int(tr, "points"))
    return [(rank, pid, points) for pid, (rank, points) in seen.items()]


async def scrape_ranking_points(db) -> int:
    """Populate current rank + points for all ranked players from the ATP
    rankings page. This is the authoritative source for points; run it before
    (or instead of) the per-player hero enrichment."""
    try:
        rows = await asyncio.to_thread(fetch_ranking_rows)
    except Exception as e:
        print(f"Failed to fetch ATP rankings page: {e}")
        return 0

    known = {r[0] for r in await db.execute(text("SELECT id FROM players"))}
    today = date.today()
    updated = 0
    for rank, pid, points in rows:
        if pid not in known:
            continue  # FK: skip players not in our table (juniors, etc.)
        await db.execute(UPSERT_RANK_POINTS, {
            "player_id": pid, "rank": rank, "points": points, "week_date": today,
        })
        updated += 1
    await db.commit()
    print(f"Ranking points: updated {updated}/{len(rows)} ranked players "
          f"(week_date={today})")
    return updated


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
    parser = argparse.ArgumentParser(description="Scrape ATP rankings + hero API")
    parser.add_argument("--all", action="store_true",
                        help="scrape every player, not just recently active ones")
    parser.add_argument("--days", type=int, default=365,
                        help="activity window in days (default 365)")
    parser.add_argument("--limit", type=int, default=None,
                        help="max players to scrape (for testing)")
    parser.add_argument("--points-only", action="store_true",
                        help="only refresh rank+points from the rankings page "
                             "(skip the slow per-player hero enrichment)")
    args = parser.parse_args()

    from database import AsyncSessionLocal, engine
    async with AsyncSessionLocal() as db:
        # Authoritative rank+points first, then per-player enrichment.
        await scrape_ranking_points(db)
        if not args.points_only:
            await scrape_atp_rankings(
                db,
                active_within_days=None if args.all else args.days,
                limit=args.limit,
            )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())

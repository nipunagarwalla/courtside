"""Scrape the ATP tournament calendar and upsert missing tournaments.

Usage (from backend/):  python -m scrapers.atp_schedule

TennisMyLife only publishes a tournament once it has match data, so current
and upcoming events (and very recent ones) are missing until play starts.
The ATP calendar endpoint lists the full season up front, so this fills the
gap. Tournament IDs use the same `{year}-{atpEventId}` scheme as the TML
loader, so re-loading TML later just no-ops on these rows.
"""
import asyncio
import re
from datetime import date

import requests
from sqlalchemy import text

CALENDAR_URL = "https://www.atptour.com/en/-/tournaments/calendar/tour"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.atptour.com/en/tournaments",
    "Accept": "application/json",
}

TIER_MAP = {"250": "ATP 250", "500": "ATP 500", "1000": "Masters 1000", "GS": "Grand Slam"}
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}

# Insert only; never clobber an existing (e.g. TennisMyLife) tournament row.
INSERT_TOURNAMENT = text("""
    INSERT INTO tournaments (id, name, tour, year, surface, tier, country, city,
                             start_date, end_date, prize_money, draw_size)
    VALUES (:id, :name, 'atp', :year, :surface, :tier, :country, :city,
            :start_date, :end_date, :prize_money, :draw_size)
    ON CONFLICT (id) DO NOTHING
""")


def _parse_dates(formatted: str) -> tuple[date | None, date | None]:
    """'13 - 19 July, 2026' or '29 June - 5 July, 2026' -> (start, end)."""
    parts = formatted.split(" - ")
    if len(parts) != 2:
        return None, None
    rm = re.match(r"(\d{1,2})\s+([A-Za-z]+),?\s*(\d{4})", parts[1].strip())
    if not rm:
        return None, None
    end_day, end_month, year = int(rm.group(1)), rm.group(2), int(rm.group(3))
    lm = re.match(r"(\d{1,2})(?:\s+([A-Za-z]+))?", parts[0].strip())
    if not lm:
        return None, None
    start_month = lm.group(2) or end_month
    try:
        start = date(year, MONTHS[start_month], int(lm.group(1)))
        end = date(year, MONTHS[end_month], end_day)
    except (KeyError, ValueError):
        return None, None
    return start, end


def _prize_money(details: str | None) -> int | None:
    if not details:
        return None
    digits = re.sub(r"[^\d]", "", details)
    return int(digits) if digits else None


def parse_calendar(payload: dict) -> list[dict]:
    """Flatten the calendar JSON into tournament row dicts (singles Tour only)."""
    rows = []
    for group in payload.get("TournamentDates") or []:
        for t in group.get("Tournaments") or []:
            tier = TIER_MAP.get(t.get("Type"))
            if tier is None or t.get("EventType") != "Tour" or not t.get("SglDrawSize"):
                continue  # skip team events (UC/DCR/LVR), challengers, ITF
            start, end = _parse_dates(t.get("FormattedDate") or "")
            if start is None:
                continue
            location = t.get("Location") or ""
            city = location.split(",")[0].strip() or t.get("Name")
            country = location.split(",")[-1].strip() if "," in location else None
            rows.append({
                "id": f"{start.year}-{t['Id']}",
                "name": city,
                "year": start.year,
                "surface": t.get("Surface"),
                "tier": tier,
                "country": country,
                "city": city,
                "start_date": start,
                "end_date": end,
                "prize_money": _prize_money(t.get("PrizeMoneyDetails")),
                "draw_size": t.get("SglDrawSize"),
            })
    return rows


def fetch_calendar_rows() -> list[dict]:
    r = requests.get(CALENDAR_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return parse_calendar(r.json())


async def scrape_atp_calendar(db) -> int:
    """Insert any calendar tournaments not already in the DB. Returns count added."""
    try:
        rows = await asyncio.to_thread(fetch_calendar_rows)
    except Exception as e:
        print(f"Failed to fetch ATP calendar: {e}")
        return 0

    before = (await db.execute(text("SELECT COUNT(*) FROM tournaments"))).scalar()
    for row in rows:
        await db.execute(INSERT_TOURNAMENT, row)
    await db.commit()
    after = (await db.execute(text("SELECT COUNT(*) FROM tournaments"))).scalar()
    added = after - before
    print(f"ATP calendar: {len(rows)} singles Tour events parsed, {added} new added")
    return added


async def _main():
    from database import AsyncSessionLocal, engine
    async with AsyncSessionLocal() as db:
        await scrape_atp_calendar(db)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())

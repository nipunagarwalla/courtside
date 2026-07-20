"""Backfill historical rankings + player DOBs from TennisMyLife CSVs.

Usage (from backend/):  python -m loaders.rankings_backfill

The Prompt-2 loader stored matches but not the per-match rank/points/age
columns. The ML features need "rank at match date", so this re-reads the
yearly CSVs and:
  1. inserts one rankings row per (player, tourney_date) observation
     (ranking_type 'standard', ON CONFLICT DO NOTHING — idempotent)
  2. fills players.dob estimated from the age columns (dob is not in any
     of our sources; tourney_date minus age-in-years is accurate to ~1 day)
"""
import asyncio
import io
from datetime import date, timedelta

import pandas as pd
import requests
from sqlalchemy import text

from database import engine
from loaders.tennismylife import API_URL, MAIN_FILE_RE, to_int, to_date

INSERT_RANKING = text("""
    INSERT INTO rankings (player_id, tour, rank, points, ranking_type, week_date)
    VALUES (:player_id, 'atp', :rank, :points, 'standard', :week_date)
    ON CONFLICT (player_id, week_date, ranking_type) DO NOTHING
""")

CHUNK = 2000


def observations_from_file(csv_text):
    df = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)
    ranks = {}   # (player_id, date) -> (rank, points)
    dobs = {}    # player_id -> estimated dob
    for row in df.itertuples(index=False):
        d = to_date(row.tourney_date)
        if not d:
            continue
        for prefix, pid in (("winner", row.winner_id), ("loser", row.loser_id)):
            if not pid:
                continue
            rank = to_int(getattr(row, f"{prefix}_rank"))
            if rank is not None:
                ranks.setdefault((pid, d), (rank, to_int(getattr(row, f"{prefix}_rank_points"))))
            try:
                age = float(getattr(row, f"{prefix}_age"))
                if age > 10:
                    dob = d - timedelta(days=age * 365.25)
                    # keep the estimate from the earliest observation
                    if pid not in dobs or d < dobs[pid][1]:
                        dobs[pid] = (dob, d)
            except (TypeError, ValueError):
                pass
    return ranks, dobs


async def backfill():
    listing = requests.get(API_URL, timeout=60).json()
    files = sorted(
        (f for f in listing["files"] if MAIN_FILE_RE.match(f["name"])),
        key=lambda f: f["name"],
    )
    print(f"{len(files)} files to process")

    # The CSVs keep gaining matches after our Prompt-2 load, so they can
    # reference players we never inserted — skip those (FK on rankings).
    async with engine.connect() as conn:
        known_players = {r[0] for r in await conn.execute(text("SELECT id FROM players"))}
    print(f"{len(known_players)} known players")

    all_dobs = {}
    total_rank_rows = 0
    for f in files:
        csv_text = requests.get(f["url"], timeout=120).text
        ranks, dobs = observations_from_file(csv_text)
        for pid, (dob, seen) in dobs.items():
            if pid not in all_dobs or seen < all_dobs[pid][1]:
                all_dobs[pid] = (dob, seen)

        rows = [
            {"player_id": pid, "rank": rank, "points": points, "week_date": d}
            for (pid, d), (rank, points) in ranks.items()
            if pid in known_players
        ]
        async with engine.begin() as conn:
            for i in range(0, len(rows), CHUNK):
                await conn.execute(INSERT_RANKING, rows[i:i + CHUNK])
        total_rank_rows += len(rows)
        print(f"{f['name']}: {len(rows)} rank observations")

    dob_rows = [{"pid": pid, "dob": dob.date() if hasattr(dob, 'date') else dob}
                for pid, (dob, _) in all_dobs.items() if pid in known_players]
    async with engine.begin() as conn:
        for i in range(0, len(dob_rows), CHUNK):
            await conn.execute(
                text("UPDATE players SET dob = :dob WHERE id = :pid AND dob IS NULL"),
                dob_rows[i:i + CHUNK],
            )
    print(f"Done. {total_rank_rows} rank observations, {len(dob_rows)} player DOBs set")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(backfill())

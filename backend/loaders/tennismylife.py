"""Load historical ATP singles match data from TennisMyLife.

Usage (from backend/):  python -m loaders.tennismylife

Fetches the file listing from the TennisMyLife API, downloads the yearly
main-tour CSVs (doubles/challengers/futures/qualifying are skipped), and
upserts players, tournaments and matches. Fully idempotent: every insert
uses ON CONFLICT DO NOTHING.
"""
import asyncio
import io
import re
from datetime import date, datetime, timedelta

import pandas as pd
import requests
from sqlalchemy import text

from database import engine

API_URL = "https://stats.tennismylife.org/api/data-files"

# Only yearly main-tour files like "2024.csv" — skips *_challenger.csv,
# atp_quali/*, ATP_Database.csv and the ongoing_tourneys metadata files.
MAIN_FILE_RE = re.compile(r"^\d{4}\.csv$")

TIER_MAP = {
    "G": "Grand Slam",
    "M": "Masters 1000",
    "500": "ATP 500",
    "250": "ATP 250",
    "F": "Tour Finals",
    "D": "Davis Cup",
    "O": "Olympics",
    "A": "ATP",
}

ATP_POINTS = {
    "Grand Slam":   {"W": 2000, "F": 1200, "SF": 720, "QF": 360, "R16": 180, "R32": 90, "R64": 45, "R128": 10},
    "Masters 1000": {"W": 1000, "F": 600,  "SF": 360, "QF": 180, "R16": 90,  "R32": 45, "R64": 25, "R128": 10},
    "ATP 500":      {"W": 500,  "F": 300,  "SF": 180, "QF": 90,  "R16": 45,  "R32": 20},
    "ATP 250":      {"W": 250,  "F": 150,  "SF": 90,  "QF": 45,  "R16": 20,  "R32": 0},
}

NEXT_ROUND = {"R128": "R64", "R64": "R32", "R32": "R16", "R16": "QF", "QF": "SF", "SF": "F", "F": "W"}

RANKINGS_WINDOW_DAYS = 30
CHUNK = 1000

INSERT_PLAYER = text("""
    INSERT INTO players (id, name, first_name, last_name, country, tour, height_cm, hand)
    VALUES (:id, :name, :first_name, :last_name, :country, 'atp', :height_cm, :hand)
    ON CONFLICT (id) DO NOTHING
""")

INSERT_TOURNAMENT = text("""
    INSERT INTO tournaments (id, name, tour, year, surface, tier, start_date, draw_size)
    VALUES (:id, :name, 'atp', :year, :surface, :tier, :start_date, :draw_size)
    ON CONFLICT (id) DO NOTHING
""")

INSERT_MATCH = text("""
    INSERT INTO matches (
        id, tournament_id, tour, year, surface, round,
        winner_id, loser_id, winner_name, loser_name, score,
        winner_sets, loser_sets, minutes,
        w_aces, w_dfs, w_svpt, w_1stin, w_1stwon, w_2ndwon, w_bpfaced, w_bpsaved,
        l_aces, l_dfs, l_svpt, l_1stin, l_1stwon, l_2ndwon, l_bpfaced, l_bpsaved,
        match_date, winner_ranking_points, loser_ranking_points
    ) VALUES (
        :id, :tournament_id, 'atp', :year, :surface, :round,
        :winner_id, :loser_id, :winner_name, :loser_name, :score,
        :winner_sets, :loser_sets, :minutes,
        :w_aces, :w_dfs, :w_svpt, :w_1stin, :w_1stwon, :w_2ndwon, :w_bpfaced, :w_bpsaved,
        :l_aces, :l_dfs, :l_svpt, :l_1stin, :l_1stwon, :l_2ndwon, :l_bpfaced, :l_bpsaved,
        :match_date, :winner_ranking_points, :loser_ranking_points
    )
    ON CONFLICT (id) DO NOTHING
""")

INSERT_RANKING = text("""
    INSERT INTO rankings (player_id, tour, rank, points, ranking_type, week_date)
    VALUES (:player_id, 'atp', :rank, :points, 'standard', :week_date)
    ON CONFLICT (player_id, week_date, ranking_type) DO NOTHING
""")


def to_int(value):
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def to_date(yyyymmdd):
    try:
        return datetime.strptime(str(yyyymmdd), "%Y%m%d").date()
    except (TypeError, ValueError):
        return None


def split_name(full_name):
    parts = full_name.split()
    if len(parts) < 2:
        return full_name or None, None
    return parts[0], " ".join(parts[1:])


def sets_won(score):
    """Count sets won by winner/loser from a score string like '4-6 7-5 6-2'."""
    w = l = 0
    for token in score.split():
        m = re.match(r"^(\d+)-(\d+)", token)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a > b:
                w += 1
            elif b > a:
                l += 1
    if w == 0 and l == 0:
        return None, None
    return w, l


def ranking_points(tier, round_name):
    """Winner earns points for the round they advance to; loser for where they exit."""
    table = ATP_POINTS.get(tier)
    if not table or not round_name:
        return None, None
    winner_pts = table.get(NEXT_ROUND.get(round_name, ""))
    loser_pts = table.get(round_name)
    return winner_pts, loser_pts


def parse_file(csv_text):
    """Parse one yearly CSV into (players, tournaments, matches, ranking_obs) row dicts."""
    df = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False)

    players, tournaments, matches = {}, {}, {}
    ranking_obs = []  # (player_id, match_date, rank, rank_points)

    for row in df.itertuples(index=False):
        tid = row.tourney_id
        round_name = row.round or None
        wid, lid = row.winner_id, row.loser_id
        if not tid or not wid or not lid:
            continue

        for pid, prefix in ((wid, "winner"), (lid, "loser")):
            if pid not in players:
                name = getattr(row, f"{prefix}_name")
                first, last = split_name(name)
                players[pid] = {
                    "id": pid,
                    "name": name,
                    "first_name": first,
                    "last_name": last,
                    "country": getattr(row, f"{prefix}_ioc") or None,
                    "height_cm": to_int(getattr(row, f"{prefix}_ht")),
                    "hand": getattr(row, f"{prefix}_hand") or None,
                }

        start_date = to_date(row.tourney_date)
        year = start_date.year if start_date else to_int(tid.split("-")[0])
        tier = TIER_MAP.get(row.tourney_level, row.tourney_level or None)
        if tid not in tournaments:
            tournaments[tid] = {
                "id": tid,
                "name": row.tourney_name,
                "year": year,
                "surface": row.surface or None,
                "tier": tier,
                "start_date": start_date,
                "draw_size": to_int(row.draw_size),
            }

        w_sets, l_sets = sets_won(row.score)
        w_pts, l_pts = ranking_points(tier, round_name)
        match_id = f"tml-{tid}-{round_name}-{wid}-vs-{lid}"
        matches[match_id] = {
            "id": match_id,
            "tournament_id": tid,
            "year": year,
            "surface": row.surface or None,
            "round": round_name,
            "winner_id": wid,
            "loser_id": lid,
            "winner_name": row.winner_name,
            "loser_name": row.loser_name,
            "score": row.score or None,
            "winner_sets": w_sets,
            "loser_sets": l_sets,
            "minutes": to_int(row.minutes),
            "w_aces": to_int(row.w_ace), "w_dfs": to_int(row.w_df),
            "w_svpt": to_int(row.w_svpt), "w_1stin": to_int(row.w_1stIn),
            "w_1stwon": to_int(row.w_1stWon), "w_2ndwon": to_int(row.w_2ndWon),
            "w_bpfaced": to_int(row.w_bpFaced), "w_bpsaved": to_int(row.w_bpSaved),
            "l_aces": to_int(row.l_ace), "l_dfs": to_int(row.l_df),
            "l_svpt": to_int(row.l_svpt), "l_1stin": to_int(row.l_1stIn),
            "l_1stwon": to_int(row.l_1stWon), "l_2ndwon": to_int(row.l_2ndWon),
            "l_bpfaced": to_int(row.l_bpFaced), "l_bpsaved": to_int(row.l_bpSaved),
            "match_date": start_date,
            "winner_ranking_points": w_pts,
            "loser_ranking_points": l_pts,
        }

        if start_date:
            ranking_obs.append((wid, start_date, to_int(row.winner_rank), to_int(row.winner_rank_points)))
            ranking_obs.append((lid, start_date, to_int(row.loser_rank), to_int(row.loser_rank_points)))

    return list(players.values()), list(tournaments.values()), list(matches.values()), ranking_obs


async def insert_rows(conn, stmt, rows):
    for i in range(0, len(rows), CHUNK):
        await conn.execute(stmt, rows[i:i + CHUNK])


async def table_count(conn, table):
    return (await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar()


async def load():
    listing = requests.get(API_URL, timeout=60).json()
    files = sorted(
        (f for f in listing["files"] if MAIN_FILE_RE.match(f["name"])),
        key=lambda f: f["name"],
    )
    print(f"{len(files)} yearly ATP files to load "
          f"({files[0]['name']} .. {files[-1]['name']})")

    recent_ranks = {}  # player_id -> (match_date, rank, rank_points)
    cutoff = date.today() - timedelta(days=RANKINGS_WINDOW_DAYS)
    total_matches = 0

    for f in files:
        year = f["name"].removesuffix(".csv")
        csv_text = requests.get(f["url"], timeout=120).text
        players, tournaments, matches, ranking_obs = parse_file(csv_text)

        async with engine.begin() as conn:
            before = await table_count(conn, "matches")
            await insert_rows(conn, INSERT_PLAYER, players)
            await insert_rows(conn, INSERT_TOURNAMENT, tournaments)
            await insert_rows(conn, INSERT_MATCH, matches)
            after = await table_count(conn, "matches")
        inserted = after - before
        total_matches += inserted
        print(f"Loading {year}... {inserted} matches inserted")

        for pid, match_date, rank, points in ranking_obs:
            if rank is None or match_date < cutoff:
                continue
            prev = recent_ranks.get(pid)
            if prev is None or match_date > prev[0]:
                recent_ranks[pid] = (match_date, rank, points)

    ranking_rows = [
        {"player_id": pid, "rank": rank, "points": points, "week_date": date.today()}
        for pid, (_, rank, points) in recent_ranks.items()
    ]
    async with engine.begin() as conn:
        await insert_rows(conn, INSERT_RANKING, ranking_rows)
    print(f"Rankings: {len(ranking_rows)} players ranked within the last "
          f"{RANKINGS_WINDOW_DAYS} days (week_date={date.today()})")
    print(f"Done. {total_matches} new matches inserted this run.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(load())

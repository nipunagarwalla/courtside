"""Backfill IBM SlamTracker point-by-point history into point_events.

Usage (from backend/):
    python -m scrapers.ibm.backfill --tournament us_open --year 2025
    python -m scrapers.ibm.backfill --tournament us_open --year 2025 --draws 1,2

Defaults to draw 1 (men's singles) — this is an ATP platform; other draws
(WS/MD/WD/XD) can be pulled explicitly via --draws.

Where possible, points are stored under the existing TennisMyLife match id
(matched by round + player last names) and the match row is tagged with
ibm_match_id/ibm_backfilled. Matches with no TML row get a standalone
`ibm-{key}-{year}-{id}` match row so the FK and replay UI still work.
"""
import argparse
import asyncio

import httpx
from sqlalchemy import text

from database import AsyncSessionLocal, engine
from .config import IBM_CONFIG, ibm_headers, all_match_ids, ROUND_NAMES
from .parser import parse_ibm_points, extract_player_names, match_winner_team

INSERT_POINT = text("""
    INSERT INTO point_events (
        match_id, set_number, game_number, point_number, server,
        score_before, score_after, p1_games, p2_games, p1_sets, p2_sets,
        winner, point_end_type, serve_speed_kmh, serve_type, rally_length,
        is_break_point, is_set_point, is_match_point, is_game_winner,
        winner_shot, serve_width, serve_depth, return_depth,
        p1_distance_m, p2_distance_m, sentence, source, raw_data
    ) VALUES (
        :match_id, :set_number, :game_number, :point_number, :server,
        :score_before, :score_after, :p1_games, :p2_games, :p1_sets, :p2_sets,
        :winner, :point_end_type, :serve_speed_kmh, :serve_type, :rally_length,
        :is_break_point, :is_set_point, :is_match_point, :is_game_winner,
        :winner_shot, :serve_width, :serve_depth, :return_depth,
        :p1_distance_m, :p2_distance_m, :sentence, :source, CAST(:raw_data AS JSONB)
    )
    ON CONFLICT (match_id, set_number, game_number, point_number) DO NOTHING
""")


def _last_name(display_name: str) -> str:
    """'C. Alcaraz' -> 'alcaraz'; 'A. de Minaur' -> 'de minaur'."""
    name = display_name.strip()
    if ". " in name:
        name = name.split(". ", 1)[1]
    return name.lower().strip()


async def _find_tml_match(db, tournament_id: str, round_: str,
                          name_a: str, name_b: str):
    """Find the TML match in this tournament+round between two players."""
    rows = (await db.execute(text("""
        SELECT id, winner_name, loser_name FROM matches
        WHERE tournament_id = :tid AND round = :round
    """), {"tid": tournament_id, "round": round_})).all()
    la, lb = _last_name(name_a), _last_name(name_b)
    for row in rows:
        wn = (row.winner_name or "").lower()
        ln = (row.loser_name or "").lower()
        if (la in wn and lb in ln) or (lb in wn and la in ln):
            return row
    return None


async def bulk_insert_points(db, points: list[dict]):
    for i in range(0, len(points), 500):
        await db.execute(INSERT_POINT, points[i:i + 500])


async def backfill_tournament(tournament_key: str, year: int,
                              draws: list[int]) -> None:
    cfg = IBM_CONFIG[tournament_key]
    if not cfg["enabled"]:
        print(f"{tournament_key}: disabled in config — skipping")
        return

    base = cfg["base_url"]
    path = cfg["feeds_path"].format(year=year)
    headers = ibm_headers(tournament_key)

    async with AsyncSessionLocal() as db:
        tournament_id = (await db.execute(text(
            "SELECT id FROM tournaments WHERE name ILIKE :name AND year = :year"
        ), {"name": cfg["tournament_name"], "year": year})).scalar()

    scraped = skipped = missing = 0
    async with httpx.AsyncClient(timeout=15) as client:
        for match_id in all_match_ids(draws):
            full_ibm_id = f"{tournament_key}-{year}-{match_id}"

            # Skip if already scraped
            async with AsyncSessionLocal() as db:
                done = (await db.execute(text("""
                    SELECT COUNT(pe.id) FROM matches m
                    JOIN point_events pe ON pe.match_id = m.id AND pe.source = 'ibm'
                    WHERE m.ibm_match_id = :imid
                """), {"imid": full_ibm_id})).scalar()
            if done:
                skipped += 1
                continue

            url = f"{base}{path}/history/{match_id}C.json"
            try:
                r = await client.get(url, headers=headers)
            except Exception as e:
                print(f"  {match_id}: fetch error — {e}")
                await asyncio.sleep(1.5)
                continue

            if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
                missing += 1
                await asyncio.sleep(0.3)
                continue
            data = r.json()
            if not data:
                missing += 1
                await asyncio.sleep(0.3)
                continue

            # Orientation: last point's MatchWinner says which IBM team won
            mw_team = match_winner_team(data)
            names = extract_player_names(data)
            if mw_team is None or len(names) < 2:
                print(f"  {match_id}: incomplete data (winner={mw_team}, "
                      f"names={names}) — skipping")
                await asyncio.sleep(0.3)
                continue
            winner_is_p1 = mw_team == 1
            winner_name, loser_name = names[mw_team], names[3 - mw_team]

            # Link to existing TML match, else create a standalone row
            round_ = ROUND_NAMES.get(int(match_id[1])) if match_id[0] == "1" else None
            async with AsyncSessionLocal() as db:
                our_id = None
                if tournament_id and round_ and match_id[0] == "1":
                    tml = await _find_tml_match(
                        db, tournament_id, round_, winner_name, loser_name)
                    if tml:
                        our_id = tml.id
                if our_id is None:
                    our_id = f"ibm-{tournament_key}-{year}-{match_id}"
                    await db.execute(text("""
                        INSERT INTO matches (id, tournament_id, tour, year,
                                             surface, round, winner_name, loser_name)
                        VALUES (:id, :tid, 'atp', :year, :surface, :round, :wn, :ln)
                        ON CONFLICT (id) DO NOTHING
                    """), {"id": our_id, "tid": tournament_id, "year": year,
                           "surface": cfg["surface"], "round": round_,
                           "wn": winner_name, "ln": loser_name})

                points = parse_ibm_points(data, our_id, winner_is_p1)
                await bulk_insert_points(db, points)
                await db.execute(text("""
                    UPDATE matches SET ibm_match_id = :imid, ibm_backfilled = true
                    WHERE id = :id
                """), {"imid": full_ibm_id, "id": our_id})
                await db.commit()

            scraped += 1
            print(f"{tournament_key} {year} {match_id}C: {len(points)} points -> {our_id}")
            await asyncio.sleep(1.5)

    print(f"Done. scraped={scraped} skipped={skipped} missing={missing}")


async def _main():
    parser = argparse.ArgumentParser(description="IBM SlamTracker backfill")
    parser.add_argument("--tournament", required=True, choices=list(IBM_CONFIG))
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--draws", default="1",
                        help="comma-separated draw numbers (1=MS 2=WS 3=MD 4=WD 5=XD)")
    args = parser.parse_args()
    draws = [int(d) for d in args.draws.split(",")]
    await backfill_tournament(args.tournament, args.year, draws)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())

"""Live polling of IBM SlamTracker during Grand Slam windows.

check_live_matches() runs every 5 minutes from APScheduler; it no-ops
outside enabled tournament windows. For each in-progress match it starts
a poll_match task that re-fetches the history feed every ~8s, stores new
points and broadcasts the latest one to SSE subscribers.

Live orientation note: while a match is in progress the winner is unknown,
so points are stored in IBM's native P1/P2 order. Once the match completes
the poller re-orients: if IBM's P2 won, stored rows are flipped so player 1
= winner, matching the rest of point_events.
"""
import asyncio
from datetime import date

import httpx
from sqlalchemy import text

from database import AsyncSessionLocal
from live import broadcaster, live_manager
from .config import IBM_CONFIG, ibm_headers, is_tournament_active
from .parser import parse_ibm_points, match_winner_team
from .backfill import bulk_insert_points

POLL_INTERVAL_S = 8

FLIP_SQL = text("""
    UPDATE point_events SET
        server = CASE server WHEN 1 THEN 2 WHEN 2 THEN 1 ELSE server END,
        winner = CASE winner WHEN 1 THEN 2 WHEN 2 THEN 1 ELSE winner END,
        p1_games = p2_games, p2_games = p1_games,
        p1_sets = p2_sets, p2_sets = p1_sets,
        p1_distance_m = p2_distance_m, p2_distance_m = p1_distance_m,
        score_before = split_part(score_before, '-', 2) || '-' || split_part(score_before, '-', 1),
        score_after = split_part(score_after, '-', 2) || '-' || split_part(score_after, '-', 1)
    WHERE match_id = :mid
""")


async def poll_match(match_id: str, tournament_key: str, year: int):
    cfg = IBM_CONFIG[tournament_key]
    our_id = f"ibm-{tournament_key}-{year}-{match_id}"
    url = (f"{cfg['base_url']}{cfg['feeds_path'].format(year=year)}"
           f"/history/{match_id}C.json")
    headers = ibm_headers(tournament_key)

    async with AsyncSessionLocal() as db:
        last_count = (await db.execute(
            text("SELECT COUNT(*) FROM point_events WHERE match_id = :mid"),
            {"mid": our_id},
        )).scalar()
        # Ensure a matches row exists so the point_events FK holds
        await db.execute(text("""
            INSERT INTO matches (id, tour, year, surface, is_live, ibm_match_id)
            VALUES (:id, 'atp', :year, :surface, true, :imid)
            ON CONFLICT (id) DO NOTHING
        """), {"id": our_id, "year": year, "surface": cfg["surface"],
               "imid": f"{tournament_key}-{year}-{match_id}"})
        await db.commit()

    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            try:
                r = await client.get(url, headers=headers)
                if r.status_code == 404:
                    break
                data = r.json()
                all_points = parse_ibm_points(data, our_id, winner_is_p1=True)
                new_points = all_points[last_count:]
                if new_points:
                    async with AsyncSessionLocal() as db:
                        await bulk_insert_points(db, new_points)
                        await db.commit()
                    await broadcaster.broadcast(
                        our_id,
                        {k: v for k, v in new_points[-1].items() if k != "raw_data"},
                    )
                    last_count += len(new_points)

                mw_team = match_winner_team(data)
                if mw_team is not None:
                    async with AsyncSessionLocal() as db:
                        if mw_team == 2:
                            # flip stored rows so player 1 = match winner
                            await db.execute(FLIP_SQL, {"mid": our_id})
                        await db.execute(text(
                            "UPDATE matches SET is_live = false, ibm_backfilled = true "
                            "WHERE id = :mid"
                        ), {"mid": our_id})
                        await db.commit()
                    break
            except Exception as e:
                print(f"Poll error {match_id}: {e}")
            await asyncio.sleep(POLL_INTERVAL_S)


async def check_live_matches():
    """Runs every 5 min from APScheduler. No-ops outside tournament windows."""
    key = is_tournament_active()
    if not key:
        return
    cfg = IBM_CONFIG[key]
    year = date.today().year
    url = f"{cfg['base_url']}{cfg['feeds_path'].format(year=year)}/matches.json"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers=ibm_headers(key))
            matches_data = r.json().get("matches", [])
        for m in matches_data:
            if m.get("status") == "InProgress" and m.get("matchId"):
                await live_manager.start(
                    f"{key}_{year}_{m['matchId']}",
                    poll_match(m["matchId"], key, year),
                )
    except Exception as e:
        print(f"check_live_matches error: {e}")

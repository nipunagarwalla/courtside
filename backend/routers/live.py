from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from live import live_manager

router = APIRouter(tags=["live"])


@router.get("/live")
async def list_live_matches(db: AsyncSession = Depends(get_db)):
    """Currently live matches with score. Empty outside tournament windows."""
    live = []
    for key in live_manager.active():
        # key format: {tournament_key}_{year}_{ibm_match_id}
        try:
            tournament_key, year, ibm_id = key.rsplit("_", 2)
        except ValueError:
            continue
        our_id = f"ibm-{tournament_key}-{year}-{ibm_id}"
        match = (await db.execute(text("""
            SELECT m.id, m.round, m.surface, m.winner_name, m.loser_name,
                   t.name AS tournament_name
            FROM matches m
            LEFT JOIN tournaments t ON m.tournament_id = t.id
            WHERE m.id = :mid
        """), {"mid": our_id})).first()
        latest = (await db.execute(text("""
            SELECT score_after, p1_games, p2_games, p1_sets, p2_sets, server
            FROM point_events WHERE match_id = :mid
            ORDER BY set_number DESC, game_number DESC, point_number DESC
            LIMIT 1
        """), {"mid": our_id})).first()
        live.append({
            "match_id": our_id,
            "tournament": match.tournament_name if match else tournament_key,
            "round": match.round if match else None,
            "surface": match.surface if match else None,
            "p1_name": match.winner_name if match else "Player 1",
            "p2_name": match.loser_name if match else "Player 2",
            "score": dict(latest._mapping) if latest else None,
        })
    return live


@router.get("/backfill/status")
async def backfill_status(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(text("""
        SELECT COALESCE(t.name, 'unknown') AS tournament, m.year,
               COUNT(DISTINCT m.id) AS matches_backfilled,
               COUNT(pe.id) AS total_points
        FROM matches m
        LEFT JOIN tournaments t ON m.tournament_id = t.id
        JOIN point_events pe ON pe.match_id = m.id AND pe.source = 'ibm'
        WHERE m.ibm_backfilled
        GROUP BY t.name, m.year
        ORDER BY m.year DESC
    """))
    return [dict(r._mapping) for r in rows]

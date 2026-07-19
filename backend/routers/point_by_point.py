from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

router = APIRouter(prefix="/matches", tags=["point-by-point"])


@router.get("/{match_id}/points")
async def get_match_points(match_id: str, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(
        text("SELECT 1 FROM matches WHERE id = :mid"), {"mid": match_id}
    )).first()
    if exists is None:
        raise HTTPException(status_code=404, detail="Match not found")

    rows = await db.execute(text("""
        SELECT set_number, game_number, point_number, server, score_before,
               score_after, p1_games, p2_games, p1_sets, p2_sets, winner,
               point_end_type, serve_speed_kmh, rally_length,
               is_break_point, is_set_point, is_match_point, sentence
        FROM point_events
        WHERE match_id = :mid
        ORDER BY set_number, game_number, point_number
    """), {"mid": match_id})

    sets: dict[int, dict] = {}
    for row in rows:
        point = dict(row._mapping)
        set_number = point.pop("set_number")
        s = sets.setdefault(set_number, {"set_number": set_number, "points": []})
        s["points"].append(point)

    return {
        "match_id": match_id,
        "has_data": bool(sets),
        "sets": [sets[k] for k in sorted(sets)],
    }

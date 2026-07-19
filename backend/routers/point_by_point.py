from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from scrapers.infosys.pipeline import scrape_match_on_demand

router = APIRouter(prefix="/matches", tags=["point-by-point"])

POINT_COLUMNS = """
    set_number, game_number, point_number, server, score_before,
    score_after, p1_games, p2_games, p1_sets, p2_sets, winner,
    point_end_type, serve_speed_kmh, serve_type, rally_length,
    is_break_point, is_set_point, is_match_point, is_game_winner,
    winner_shot, sentence
"""


async def _match_exists(db, match_id: str) -> bool:
    row = (await db.execute(
        text("SELECT 1 FROM matches WHERE id = :mid"), {"mid": match_id}
    )).first()
    return row is not None


async def _get_point_rows(db, match_id: str):
    result = await db.execute(text(f"""
        SELECT {POINT_COLUMNS}
        FROM point_events
        WHERE match_id = :mid
        ORDER BY set_number, game_number, point_number
    """), {"mid": match_id})
    return result.all()


def format_points_response(match_id: str, rows) -> dict:
    """Group flat point rows into sets -> games -> points.

    Player 1 is always the match winner, player 2 the loser (parser
    convention). Set game-counts come from counting game winners.
    """
    sets: dict[int, dict] = {}
    for row in rows:
        point = dict(row._mapping)
        set_number = point.pop("set_number")
        game_number = point.pop("game_number")
        s = sets.setdefault(set_number, {
            "set_number": set_number, "p1_games": 0, "p2_games": 0, "_games": {},
        })
        g = s["_games"].setdefault(game_number, {
            "game_number": game_number,
            "server": point["server"],
            "winner": None,
            "points": [],
        })
        g["points"].append(point)
        if point["is_game_winner"]:
            g["winner"] = point["winner"]

    for s in sets.values():
        for g in s["_games"].values():
            if g["winner"] == 1:
                s["p1_games"] += 1
            elif g["winner"] == 2:
                s["p2_games"] += 1

    return {
        "match_id": match_id,
        "has_data": bool(sets),
        "sets": [
            {
                "set_number": s["set_number"],
                "p1_games": s["p1_games"],
                "p2_games": s["p2_games"],
                "games": [s["_games"][k] for k in sorted(s["_games"])],
            }
            for s in (sets[k] for k in sorted(sets))
        ],
    }


@router.get("/{match_id}/points")
async def get_match_points(match_id: str, db: AsyncSession = Depends(get_db)):
    if not await _match_exists(db, match_id):
        raise HTTPException(status_code=404, detail="Match not found")

    rows = await _get_point_rows(db, match_id)
    if rows:
        return format_points_response(match_id, rows)

    # No cached data — scrape on demand (first request takes a few seconds)
    try:
        success = await scrape_match_on_demand(match_id, db)
    except Exception as e:
        print(f"on-demand scrape failed for {match_id}: {e}")
        success = False

    if success:
        rows = await _get_point_rows(db, match_id)
        if rows:
            return format_points_response(match_id, rows)

    return {
        "match_id": match_id,
        "has_data": False,
        "sets": [],
        "message": "Point-by-point data not available for this match",
    }


@router.get("/{match_id}/points/set/{set_number}/game/{game_number}")
async def get_game_points(
    match_id: str, set_number: int, game_number: int,
    db: AsyncSession = Depends(get_db),
):
    if not await _match_exists(db, match_id):
        raise HTTPException(status_code=404, detail="Match not found")
    result = await db.execute(text(f"""
        SELECT {POINT_COLUMNS}
        FROM point_events
        WHERE match_id = :mid AND set_number = :set AND game_number = :game
        ORDER BY point_number
    """), {"mid": match_id, "set": set_number, "game": game_number})
    points = [dict(r._mapping) for r in result]
    return {
        "match_id": match_id,
        "set_number": set_number,
        "game_number": game_number,
        "points": points,
    }


@router.get("/{match_id}/stats")
async def get_match_keystats(match_id: str, db: AsyncSession = Depends(get_db)):
    if not await _match_exists(db, match_id):
        raise HTTPException(status_code=404, detail="Match not found")
    result = await db.execute(text("""
        SELECT set_number, player, stat_name, value
        FROM match_keystats
        WHERE match_id = :mid
        ORDER BY set_number, id
    """), {"mid": match_id})

    # Pivot into one row per (set, stat): p1 = match winner, p2 = loser
    stats: dict[tuple, dict] = {}
    for row in result:
        key = (row.set_number, row.stat_name)
        entry = stats.setdefault(key, {
            "set_number": row.set_number, "stat_name": row.stat_name,
            "p1": None, "p2": None,
        })
        entry[f"p{row.player}"] = row.value

    return {
        "match_id": match_id,
        "has_data": bool(stats),
        "stats": list(stats.values()),
    }

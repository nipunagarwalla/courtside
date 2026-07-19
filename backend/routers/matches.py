from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("")
async def list_matches(
    player_id: str | None = None,
    tournament_id: str | None = None,
    year: int | None = None,
    surface: str | None = None,
    round: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    clauses = []
    params = {"limit": limit, "offset": offset}
    if player_id:
        clauses.append("(m.winner_id = :pid OR m.loser_id = :pid)")
        params["pid"] = player_id
    if tournament_id:
        clauses.append("m.tournament_id = :tid")
        params["tid"] = tournament_id
    if year is not None:
        clauses.append("m.year = :year")
        params["year"] = year
    if surface:
        clauses.append("m.surface ILIKE :surface")
        params["surface"] = surface
    if round:
        clauses.append("m.round = :round")
        params["round"] = round
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = await db.execute(text(f"""
        SELECT m.id, t.name AS tournament_name, m.surface, m.round,
               m.winner_name, m.loser_name, m.score, m.match_date, m.minutes
        FROM matches m
        LEFT JOIN tournaments t ON m.tournament_id = t.id
        {where}
        ORDER BY m.match_date DESC NULLS LAST, m.id
        LIMIT :limit OFFSET :offset
    """), params)
    return [dict(row._mapping) for row in rows]


@router.get("/{match_id}")
async def get_match(match_id: str, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(text("""
        SELECT m.*, t.name AS tournament_name, t.tier AS tournament_tier
        FROM matches m
        LEFT JOIN tournaments t ON m.tournament_id = t.id
        WHERE m.id = :mid
    """), {"mid": match_id})).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return dict(row._mapping)

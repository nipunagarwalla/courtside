from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

router = APIRouter(prefix="/tournaments", tags=["tournaments"])

# Tournaments in our data usually have no end_date; assume a two-week window
# when deciding whether one is still in progress.
STATUS_SQL = """
    CASE
        WHEN t.start_date IS NULL THEN NULL
        WHEN t.start_date > CURRENT_DATE THEN 'upcoming'
        WHEN COALESCE(t.end_date, t.start_date + 13) >= CURRENT_DATE THEN 'in_progress'
        ELSE 'completed'
    END AS status
"""


@router.get("")
async def list_tournaments(
    year: int | None = None,
    surface: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    clauses = []
    params = {"limit": limit, "offset": offset}
    if year is not None:
        clauses.append("t.year = :year")
        params["year"] = year
    if surface:
        clauses.append("t.surface ILIKE :surface")
        params["surface"] = surface
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = await db.execute(text(f"""
        SELECT t.id, t.name, t.year, t.surface, t.tier, t.country, t.city,
               t.start_date, t.end_date, t.draw_size, {STATUS_SQL}
        FROM tournaments t
        {where}
        ORDER BY t.start_date DESC NULLS LAST, t.name
        LIMIT :limit OFFSET :offset
    """), params)
    return [dict(row._mapping) for row in rows]


@router.get("/{tournament_id}")
async def get_tournament(tournament_id: str, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(text(f"""
        SELECT t.id, t.name, t.tour, t.year, t.surface, t.tier, t.country,
               t.city, t.start_date, t.end_date, t.prize_money, t.draw_size,
               {STATUS_SQL}
        FROM tournaments t
        WHERE t.id = :tid
    """), {"tid": tournament_id})).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Tournament not found")

    matches = await db.execute(text("""
        SELECT id, round, winner_id, winner_name, loser_id, loser_name,
               score, match_date, minutes
        FROM matches
        WHERE tournament_id = :tid
        ORDER BY match_date, id
    """), {"tid": tournament_id})
    result = dict(row._mapping)
    result["matches"] = [dict(m._mapping) for m in matches]
    return result

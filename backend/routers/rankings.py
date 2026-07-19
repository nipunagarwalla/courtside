from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

router = APIRouter(prefix="/rankings", tags=["rankings"])


@router.get("")
async def list_rankings(
    limit: int = Query(100, ge=1, le=1000),
    type: str = Query("standard"),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(text("""
        WITH latest AS (
            SELECT MAX(week_date) AS week_date FROM rankings WHERE ranking_type = :type
        )
        SELECT cur.rank, cur.player_id, p.name, p.country, cur.points,
               prev.rank - cur.rank AS movement
        FROM rankings cur
        JOIN latest ON cur.week_date = latest.week_date
        JOIN players p ON p.id = cur.player_id
        LEFT JOIN LATERAL (
            SELECT rank FROM rankings
            WHERE player_id = cur.player_id
              AND ranking_type = :type
              AND week_date < cur.week_date
            ORDER BY week_date DESC
            LIMIT 1
        ) prev ON true
        WHERE cur.ranking_type = :type
        ORDER BY cur.rank
        LIMIT :limit
    """), {"type": type, "limit": limit})
    return [dict(row._mapping) for row in rows]

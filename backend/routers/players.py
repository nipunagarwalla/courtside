from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("/{player_id}")
async def get_player(player_id: str, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(text("""
        SELECT
            p.id, p.name, p.first_name, p.last_name, p.country, p.tour,
            p.dob, p.turned_pro, p.height_cm, p.hand,
            p.coach, p.weight_kg, p.career_prize,
            p.hi_rank, p.hi_rank_date,
            p.ytd_wins, p.ytd_losses, p.ytd_titles,
            p.career_wins, p.career_losses, p.career_titles,
            r.rank AS current_rank, r.week_date AS rank_date
        FROM players p
        LEFT JOIN LATERAL (
            SELECT rank, week_date FROM rankings
            WHERE player_id = p.id AND ranking_type = 'standard'
            ORDER BY week_date DESC
            LIMIT 1
        ) r ON true
        WHERE upper(p.id) = upper(:pid)
    """), {"pid": player_id})).first()

    if row is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return dict(row._mapping)

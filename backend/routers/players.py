import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

router = APIRouter(prefix="/players", tags=["players"])

# Latest standard-ranking row for a player, as a reusable lateral join.
CURRENT_RANK_LATERAL = """
    LEFT JOIN LATERAL (
        SELECT rank, points, week_date FROM rankings
        WHERE player_id = p.id AND ranking_type = 'standard'
        ORDER BY week_date DESC
        LIMIT 1
    ) r ON true
"""


def atp_profile_url(name: str, player_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    # ATP URLs use lowercase player IDs (DB stores them uppercase)
    return f"https://www.atptour.com/en/players/{slug}/{player_id.lower()}/overview"


@router.get("")
async def list_players(
    search: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    where = ""
    params = {"limit": limit, "offset": offset}
    if search:
        where = "WHERE p.name ILIKE :search"
        params["search"] = f"%{search}%"
    rows = await db.execute(text(f"""
        SELECT p.id, p.name, p.country, p.tour,
               r.rank AS current_rank, r.points AS current_points
        FROM players p
        {CURRENT_RANK_LATERAL}
        {where}
        ORDER BY r.rank NULLS LAST, p.name
        LIMIT :limit OFFSET :offset
    """), params)
    return [dict(row._mapping) for row in rows]


@router.get("/{player_id}")
async def get_player(player_id: str, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(text(f"""
        SELECT
            p.id, p.name, p.first_name, p.last_name, p.country, p.tour,
            p.dob, p.turned_pro, p.height_cm, p.hand,
            p.coach, p.weight_kg, p.career_prize,
            p.hi_rank, p.hi_rank_date,
            p.ytd_wins, p.ytd_losses, p.ytd_titles,
            p.career_wins, p.career_losses, p.career_titles,
            r.rank AS current_rank, r.points AS current_points
        FROM players p
        {CURRENT_RANK_LATERAL}
        WHERE upper(p.id) = upper(:pid)
    """), {"pid": player_id})).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Player not found")

    player = dict(row._mapping)
    pid = player["id"]

    surface_rows = await db.execute(text("""
        SELECT surface,
               COUNT(*) FILTER (WHERE winner_id = :pid) AS wins,
               COUNT(*) AS total
        FROM matches
        WHERE winner_id = :pid OR loser_id = :pid
        GROUP BY surface
    """), {"pid": pid})
    wins = total = 0
    by_surface = {}
    for srow in surface_rows:
        wins += srow.wins
        total += srow.total
        if srow.surface:
            by_surface[srow.surface.lower()] = (srow.wins, srow.total)

    def rate(pair):
        if not pair or not pair[1]:
            return None
        return round(pair[0] / pair[1], 3)

    player["win_rate_overall"] = round(wins / total, 3) if total else None
    for surface in ("hard", "clay", "grass"):
        player[f"win_rate_{surface}"] = rate(by_surface.get(surface))

    # Career W/L: prefer ATP-enriched values, fall back to our match data
    losses = total - wins
    player["career_wins"] = player["career_wins"] if player["career_wins"] is not None else wins
    player["career_losses"] = player["career_losses"] if player["career_losses"] is not None else losses

    recent = await db.execute(text("""
        SELECT m.id AS match_id, m.match_date, m.score, m.round, m.surface,
               t.name AS tournament,
               CASE WHEN m.winner_id = :pid THEN 'W' ELSE 'L' END AS result,
               CASE WHEN m.winner_id = :pid THEN m.loser_id ELSE m.winner_id END AS opponent_id,
               CASE WHEN m.winner_id = :pid THEN m.loser_name ELSE m.winner_name END AS opponent_name
        FROM matches m
        LEFT JOIN tournaments t ON m.tournament_id = t.id
        WHERE m.winner_id = :pid OR m.loser_id = :pid
        ORDER BY m.match_date DESC NULLS LAST, m.id
        LIMIT 10
    """), {"pid": pid})
    player["recent_matches"] = [dict(row._mapping) for row in recent]
    player["atp_profile_url"] = atp_profile_url(player["name"], pid)
    return player

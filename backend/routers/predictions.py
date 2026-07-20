from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from ml.features import build_feature_row_for_pair

router = APIRouter(tags=["predictions"])

SURFACES = {"Hard", "Clay", "Grass"}


def _predictor_or_503(request: Request):
    predictor = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Model not trained yet. Run python -m ml.train first.",
        )
    return predictor


async def _player_summary(db, pid: str):
    row = (await db.execute(text("""
        SELECT p.id, p.name, p.country, r.rank AS current_rank
        FROM players p
        LEFT JOIN LATERAL (
            SELECT rank FROM rankings
            WHERE player_id = p.id AND ranking_type = 'standard'
            ORDER BY week_date DESC LIMIT 1
        ) r ON true
        WHERE upper(p.id) = upper(:pid)
    """), {"pid": pid})).first()
    return dict(row._mapping) if row else None


async def _context(db, p1: str, p2: str, surface: str):
    h2h = (await db.execute(text("""
        SELECT COUNT(*) FILTER (WHERE winner_id = :p1) AS p1_wins,
               COUNT(*) FILTER (WHERE winner_id = :p2) AS p2_wins
        FROM matches
        WHERE (winner_id = :p1 AND loser_id = :p2)
           OR (winner_id = :p2 AND loser_id = :p1)
    """), {"p1": p1, "p2": p2})).first()

    async def surface_winrate(pid):
        row = (await db.execute(text("""
            SELECT COUNT(*) FILTER (WHERE winner_id = :pid) AS wins, COUNT(*) AS total
            FROM matches
            WHERE (winner_id = :pid OR loser_id = :pid) AND surface ILIKE :surface
              AND match_date >= CURRENT_DATE - 1095
        """), {"pid": pid, "surface": surface})).first()
        return round(row.wins / row.total, 3) if row.total else None

    async def form10(pid):
        rows = await db.execute(text("""
            SELECT CASE WHEN winner_id = :pid THEN 'W' ELSE 'L' END AS r
            FROM matches WHERE winner_id = :pid OR loser_id = :pid
            ORDER BY match_date DESC NULLS LAST, id LIMIT 10
        """), {"pid": pid})
        return [r.r for r in rows]

    return {
        "h2h_p1_wins": h2h.p1_wins,
        "h2h_p2_wins": h2h.p2_wins,
        "p1_surface_winrate": await surface_winrate(p1),
        "p2_surface_winrate": await surface_winrate(p2),
        "p1_form_last10": await form10(p1),
        "p2_form_last10": await form10(p2),
    }


@router.get("/predict")
async def predict(
    request: Request,
    p1: str = Query(...),
    p2: str = Query(...),
    surface: str = Query("Hard"),
    tier: str = Query("Masters 1000"),
    round: str = Query("SF"),
    db: AsyncSession = Depends(get_db),
):
    predictor = _predictor_or_503(request)
    if surface not in SURFACES:
        raise HTTPException(status_code=422, detail=f"surface must be one of {sorted(SURFACES)}")

    player1 = await _player_summary(db, p1)
    player2 = await _player_summary(db, p2)
    if player1 is None or player2 is None:
        missing = p1 if player1 is None else p2
        raise HTTPException(status_code=404, detail=f"Player not found: {missing}")
    p1, p2 = player1["id"], player2["id"]

    features = await build_feature_row_for_pair(db, p1, p2, surface, tier, round)
    if features is None:
        raise HTTPException(status_code=422, detail="Not enough data for these players")

    return {
        "p1": player1,
        "p2": player2,
        "prediction": predictor.predict(features),
        "context": await _context(db, p1, p2, surface),
    }


@router.get("/predictions/upcoming")
async def upcoming(request: Request, db: AsyncSession = Depends(get_db)):
    predictor = _predictor_or_503(request)
    matches = (await db.execute(text("""
        SELECT m.id, m.match_date, m.surface, m.round,
               m.winner_id AS p1_id, m.loser_id AS p2_id,
               m.winner_name AS p1_name, m.loser_name AS p2_name,
               t.name AS tournament, t.tier
        FROM matches m
        LEFT JOIN tournaments t ON m.tournament_id = t.id
        WHERE m.match_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 7
          AND m.winner_id IS NOT NULL AND m.loser_id IS NOT NULL
          AND m.surface IS NOT NULL
        ORDER BY m.match_date
        LIMIT 50
    """))).all()

    out = []
    for m in matches:
        features = await build_feature_row_for_pair(
            db, m.p1_id, m.p2_id, m.surface, m.tier, m.round,
            as_of=m.match_date,
        )
        if features is None:
            continue
        p1 = await _player_summary(db, m.p1_id)
        p2 = await _player_summary(db, m.p2_id)
        out.append({
            "match_id": m.id,
            "match_date": m.match_date,
            "tournament": m.tournament,
            "tier": m.tier,
            "round": m.round,
            "surface": m.surface,
            "p1": p1,
            "p2": p2,
            "prediction": predictor.predict(features),
        })
    return out

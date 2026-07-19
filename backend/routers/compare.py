from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db

router = APIRouter(prefix="/compare", tags=["compare"])

H2H_SURFACES = ("hard", "clay", "grass")
H2H_TIERS = ("Grand Slam", "Masters 1000", "ATP 500", "ATP 250")


async def _player_summary(db, pid):
    row = (await db.execute(text("""
        SELECT p.id, p.name, p.country,
               p.career_titles, p.career_wins, p.career_losses,
               r.rank AS current_rank, r.points AS current_points
        FROM players p
        LEFT JOIN LATERAL (
            SELECT rank, points FROM rankings
            WHERE player_id = p.id AND ranking_type = 'standard'
            ORDER BY week_date DESC
            LIMIT 1
        ) r ON true
        WHERE upper(p.id) = upper(:pid)
    """), {"pid": pid})).first()
    return dict(row._mapping) if row else None


async def _surface_win_rates(db, pid):
    rows = await db.execute(text("""
        SELECT surface,
               COUNT(*) FILTER (WHERE winner_id = :pid) AS wins,
               COUNT(*) AS total
        FROM matches
        WHERE winner_id = :pid OR loser_id = :pid
        GROUP BY surface
    """), {"pid": pid})
    wins = total = 0
    per_surface = {}
    for row in rows:
        wins += row.wins
        total += row.total
        if row.surface:
            per_surface[row.surface.lower()] = (row.wins, row.total)
    rates = {"overall": round(wins / total, 3) if total else None}
    for surface in H2H_SURFACES:
        w, t = per_surface.get(surface, (0, 0))
        rates[surface] = round(w / t, 3) if t else None
    return rates, wins, total


async def _recent_form(db, pid):
    rows = await db.execute(text("""
        SELECT CASE WHEN winner_id = :pid THEN 'W' ELSE 'L' END AS result
        FROM matches
        WHERE winner_id = :pid OR loser_id = :pid
        ORDER BY match_date DESC NULLS LAST, id
        LIMIT 10
    """), {"pid": pid})
    form = [row.result for row in rows]
    pct = round(100 * form.count("W") / len(form), 1) if form else None
    return form, pct


async def _title_counts(db, pid):
    row = (await db.execute(text("""
        SELECT COUNT(*) AS titles,
               COUNT(*) FILTER (WHERE t.tier = 'Grand Slam') AS slam_titles,
               COUNT(*) FILTER (WHERE t.tier = 'Masters 1000') AS masters_titles
        FROM matches m
        JOIN tournaments t ON m.tournament_id = t.id
        WHERE m.winner_id = :pid AND m.round = 'F'
    """), {"pid": pid})).first()
    return row


async def _serve_stats(db, pid):
    row = (await db.execute(text("""
        SELECT
            COUNT(*) AS matches,
            AVG(CASE WHEN winner_id = :pid THEN w_aces ELSE l_aces END) AS avg_aces,
            AVG(CASE WHEN winner_id = :pid THEN w_dfs ELSE l_dfs END) AS avg_dfs,
            SUM(CASE WHEN winner_id = :pid THEN w_1stin ELSE l_1stin END) AS first_in,
            SUM(CASE WHEN winner_id = :pid THEN w_svpt ELSE l_svpt END) AS serve_pts,
            SUM(CASE WHEN winner_id = :pid THEN w_1stwon ELSE l_1stwon END) AS first_won,
            SUM(CASE WHEN winner_id = :pid THEN w_bpsaved ELSE l_bpsaved END) AS bp_saved,
            SUM(CASE WHEN winner_id = :pid THEN w_bpfaced ELSE l_bpfaced END) AS bp_faced
        FROM matches
        WHERE winner_id = :pid OR loser_id = :pid
    """), {"pid": pid})).first()

    def pct(num, den):
        return round(100 * num / den, 1) if num is not None and den else None

    return {
        "avg_aces_per_match": round(float(row.avg_aces), 1) if row.avg_aces is not None else None,
        "avg_dfs_per_match": round(float(row.avg_dfs), 1) if row.avg_dfs is not None else None,
        "first_serve_pct": pct(row.first_in, row.serve_pts),
        "first_serve_win_pct": pct(row.first_won, row.first_in),
        "bp_save_pct": pct(row.bp_saved, row.bp_faced),
    }


def _bucket(matches, p1, key):
    """Aggregate h2h wins grouped by `key` (a callable on the match row)."""
    out = {}
    for m in matches:
        k = key(m)
        if k is None:
            continue
        b = out.setdefault(k, {"total": 0, "p1_wins": 0, "p2_wins": 0})
        b["total"] += 1
        if m["winner_id"] == p1:
            b["p1_wins"] += 1
        else:
            b["p2_wins"] += 1
    return out


@router.get("")
async def compare(
    p1: str = Query(..., description="first player id"),
    p2: str = Query(..., description="second player id"),
    db: AsyncSession = Depends(get_db),
):
    player1 = await _player_summary(db, p1)
    player2 = await _player_summary(db, p2)
    if player1 is None or player2 is None:
        missing = p1 if player1 is None else p2
        raise HTTPException(status_code=404, detail=f"Player not found: {missing}")
    p1, p2 = player1["id"], player2["id"]  # canonical (uppercase) ids

    h2h_rows = await db.execute(text("""
        SELECT m.id AS match_id, t.name AS tournament_name, m.surface, t.tier,
               m.round, m.match_date, m.winner_id, m.score
        FROM matches m
        LEFT JOIN tournaments t ON m.tournament_id = t.id
        WHERE (m.winner_id = :p1 AND m.loser_id = :p2)
           OR (m.winner_id = :p2 AND m.loser_id = :p1)
        ORDER BY m.match_date DESC NULLS LAST, m.id
    """), {"p1": p1, "p2": p2})
    h2h_matches = [dict(row._mapping) | {"p1_won": row.winner_id == p1} for row in h2h_rows]

    p1_wins = sum(1 for m in h2h_matches if m["p1_won"])
    total = len(h2h_matches)

    by_surface = _bucket(h2h_matches, p1, lambda m: (m["surface"] or "").lower() or None)
    by_tier = _bucket(h2h_matches, p1, lambda m: m["tier"])
    by_round = _bucket(h2h_matches, p1, lambda m: m["round"])

    p1_rates, p1_w, p1_t = await _surface_win_rates(db, p1)
    p2_rates, p2_w, p2_t = await _surface_win_rates(db, p2)
    p1_form, p1_pct = await _recent_form(db, p1)
    p2_form, p2_pct = await _recent_form(db, p2)
    p1_titles = await _title_counts(db, p1)
    p2_titles = await _title_counts(db, p2)

    def career(player, computed_titles, wins, total_matches):
        return {
            "titles": player["career_titles"] if player["career_titles"] is not None else computed_titles.titles,
            "wins": player["career_wins"] if player["career_wins"] is not None else wins,
            "losses": player["career_losses"] if player["career_losses"] is not None else total_matches - wins,
            "slam_titles": computed_titles.slam_titles,
            "masters_titles": computed_titles.masters_titles,
        }

    career_stats = {
        "p1": career(player1, p1_titles, p1_w, p1_t),
        "p2": career(player2, p2_titles, p2_w, p2_t),
    }
    for player in (player1, player2):
        for k in ("career_titles", "career_wins", "career_losses"):
            player.pop(k, None)

    return {
        "player1": player1,
        "player2": player2,
        "h2h": {
            "total_matches": total,
            "p1_wins": p1_wins,
            "p2_wins": total - p1_wins,
            "p1_win_pct": round(100 * p1_wins / total, 1) if total else None,
        },
        "h2h_by_surface": {
            s: by_surface.get(s, {"total": 0, "p1_wins": 0, "p2_wins": 0})
            for s in H2H_SURFACES
        },
        "h2h_by_tier": {
            t: by_tier.get(t, {"total": 0, "p1_wins": 0, "p2_wins": 0})
            for t in H2H_TIERS
        },
        "h2h_by_round": by_round,
        "recent_form": {
            "p1_last10": p1_form,
            "p2_last10": p2_form,
            "p1_last10_pct": p1_pct,
            "p2_last10_pct": p2_pct,
        },
        "surface_win_rates": {"p1": p1_rates, "p2": p2_rates},
        "career_stats": career_stats,
        "serve_stats": {
            "p1": await _serve_stats(db, p1),
            "p2": await _serve_stats(db, p2),
        },
        "h2h_matches": h2h_matches,
    }

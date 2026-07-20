"""One-off: recompute is_set_point / is_match_point for existing Infosys rows.

Usage (from backend/):  python -m scrapers.infosys.fix_sp_mp

Uses the same compute_set_and_match_point() as the parser, driven by each
row's stored score_before / games / sets state — no re-scraping.
"""
import asyncio

from sqlalchemy import text

from database import AsyncSessionLocal, engine
from .parser import compute_set_and_match_point


async def fix():
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(text("""
            SELECT pe.id, pe.score_before, pe.p1_games, pe.p2_games,
                   pe.p1_sets, pe.p2_sets, pe.is_set_point, pe.is_match_point,
                   t.tier
            FROM point_events pe
            JOIN matches m ON pe.match_id = m.id
            LEFT JOIN tournaments t ON m.tournament_id = t.id
            WHERE pe.source = 'infosys'
        """))).all()

        updated = 0
        for row in rows:
            total_needed = 3 if row.tier == "Grand Slam" else 2
            p1s, _, p2s = (row.score_before or "0-0").partition("-")
            # Tiebreak: both players already at 6 games when the game is played
            is_tiebreak = row.p1_games == 6 and row.p2_games == 6
            sp, mp = compute_set_and_match_point(
                p1s, p2s,
                row.p1_games or 0, row.p2_games or 0,
                row.p1_sets or 0, row.p2_sets or 0,
                total_needed, is_tiebreak,
            )
            if sp != row.is_set_point or mp != row.is_match_point:
                await db.execute(text(
                    "UPDATE point_events SET is_set_point = :sp, is_match_point = :mp WHERE id = :id"
                ), {"sp": sp, "mp": mp, "id": row.id})
                updated += 1

        await db.commit()
        print(f"Checked {len(rows)} infosys points, updated {updated}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix())

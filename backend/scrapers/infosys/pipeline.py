"""On-demand Infosys scraping: find a match, pull its points, cache in DB."""
import asyncio
import time

from sqlalchemy import text

from .config import get_event_config
from .fetch import make_client, fetch_endpoint
from .parser import (
    parse_match_beats,
    parse_keystats,
    matches_our_players,
    needs_swap,
)

# Typical MS-number of the first match of each round (final = MS001).
# Scanning starts near the expected number for the round so discovery for
# late-round matches takes seconds, not minutes.
ROUND_START = {"F": 1, "SF": 2, "QF": 4, "R16": 8, "R32": 16, "R64": 32, "R128": 64}

DISCOVERY_TIME_BUDGET_S = 120

INSERT_POINT = text("""
    INSERT INTO point_events (
        match_id, set_number, game_number, point_number, server,
        score_before, score_after, p1_games, p2_games, p1_sets, p2_sets,
        winner, point_end_type, serve_speed_kmh, serve_type, rally_length,
        is_break_point, is_set_point, is_match_point, is_game_winner,
        winner_shot, sentence, source, raw_data
    ) VALUES (
        :match_id, :set_number, :game_number, :point_number, :server,
        :score_before, :score_after, :p1_games, :p2_games, :p1_sets, :p2_sets,
        :winner, :point_end_type, :serve_speed_kmh, :serve_type, :rally_length,
        :is_break_point, :is_set_point, :is_match_point, :is_game_winner,
        :winner_shot, :sentence, :source, CAST(:raw_data AS JSONB)
    )
    ON CONFLICT (match_id, set_number, game_number, point_number) DO NOTHING
""")

INSERT_KEYSTAT = text("""
    INSERT INTO match_keystats (match_id, set_number, player, stat_name, value)
    VALUES (:match_id, :set_number, :player, :stat_name, :value)
    ON CONFLICT (match_id, set_number, player, stat_name) DO NOTHING
""")


def _scan_order(round_: str | None, max_matches: int) -> list[int]:
    """Candidate MS numbers, starting near the expected slot for the round."""
    start = ROUND_START.get(round_ or "", 1)
    start = min(start, max_matches)
    return list(range(start, max_matches + 1)) + list(range(1, start))


async def find_infosys_match_id(
    year: int,
    event_id: str,
    winner_id: str,
    loser_id: str,
    round_: str | None,
    max_matches: int,
    client,
) -> tuple[str, dict] | None:
    """Try MS numbers until the payload's player IDs match ours.

    Returns (infosys_match_id, decrypted_match_beats) or None.
    """
    deadline = time.monotonic() + DISCOVERY_TIME_BUDGET_S
    misses = 0
    found_any = False
    for n in _scan_order(round_, max_matches):
        if time.monotonic() > deadline:
            print(f"  discovery timed out for event {event_id}")
            return None
        match_id = f"MS{n:03d}"
        data = await fetch_endpoint(client, "match_beats", year, event_id, match_id)
        if data is None:
            misses += 1
            # A covered event answers 200 for most nearby MS numbers; if the
            # first stretch is all 404s the event has no data at all (e.g.
            # Grand Slams) — bail instead of scanning every number.
            if not found_any and misses >= 16:
                print(f"  event {event_id}: no match-beats coverage, giving up")
                return None
            await asyncio.sleep(0.3)
            continue
        found_any = True
        if matches_our_players(data, winner_id, loser_id):
            return match_id, data
        await asyncio.sleep(0.3)
    return None


async def _store_points(db, match_beats: dict, our_match_id: str, winner_id: str) -> int:
    swap = needs_swap(match_beats, winner_id)
    points = parse_match_beats(match_beats, our_match_id, swap)
    for i in range(0, len(points), 500):
        await db.execute(INSERT_POINT, points[i:i + 500])
    return len(points)


async def _fetch_and_store_keystats(
    db, client, year: int, event_id: str, infosys_match_id: str,
    our_match_id: str, winner_id: str, match_beats: dict,
) -> None:
    data = await fetch_endpoint(client, "keystats", year, event_id, infosys_match_id)
    if not data:
        return
    swap = needs_swap(match_beats, winner_id)
    rows = parse_keystats(data, our_match_id, swap)
    if rows:
        await db.execute(INSERT_KEYSTAT, rows)


async def scrape_match_on_demand(our_match_id: str, db) -> bool:
    """Called when a user requests point-by-point data for a match.

    Returns True if data was found and stored (or already present).
    """
    existing = (await db.execute(
        text("SELECT COUNT(*) FROM point_events WHERE match_id = :mid"),
        {"mid": our_match_id},
    )).scalar()
    if existing > 0:
        return True

    match = (await db.execute(text("""
        SELECT id, tournament_id, year, round, winner_id, loser_id,
               infosys_match_id, infosys_event_id
        FROM matches WHERE id = :mid
    """), {"mid": our_match_id})).first()
    if not match or not match.winner_id or not match.loser_id:
        return False

    async with make_client() as client:
        # Fast path: IDs already discovered previously
        if match.infosys_match_id and match.infosys_event_id:
            event_id, infosys_match_id = match.infosys_event_id, match.infosys_match_id
            data = await fetch_endpoint(
                client, "match_beats", match.year, event_id, infosys_match_id
            )
            if not data:
                return False
        else:
            tournament = (await db.execute(
                text("SELECT id, name, year FROM tournaments WHERE id = :tid"),
                {"tid": match.tournament_id},
            )).first()
            if not tournament:
                return False
            cfg = get_event_config(tournament.name)
            if not cfg:
                print(f"No Infosys config for tournament: {tournament.name}")
                return False

            year = match.year or tournament.year
            result = await find_infosys_match_id(
                year=year,
                event_id=cfg["event_id"],
                winner_id=match.winner_id,
                loser_id=match.loser_id,
                round_=match.round,
                max_matches=cfg["max_matches"],
                client=client,
            )
            if not result:
                return False
            infosys_match_id, data = result
            event_id = cfg["event_id"]

            await db.execute(text("""
                UPDATE matches SET infosys_event_id = :eid, infosys_match_id = :imid
                WHERE id = :mid
            """), {"eid": event_id, "imid": infosys_match_id, "mid": our_match_id})

        n_points = await _store_points(db, data, our_match_id, match.winner_id)
        await _fetch_and_store_keystats(
            db, client, match.year, event_id, infosys_match_id,
            our_match_id, match.winner_id, data,
        )
        await db.commit()
        print(f"Scraped {our_match_id}: {n_points} points stored "
              f"(infosys {event_id}/{infosys_match_id})")
        return n_points > 0

"""Resolve player IDs + match_date for standalone IBM matches.

The IBM backfill can only link to existing TennisMyLife match rows when TML
has the tournament. For Slams TML hasn't published yet (e.g. US Open 2026),
it creates standalone rows carrying player *names* (from the point sentences)
but no winner_id/loser_id and no match_date — so those matches never show on
player profiles or sort chronologically.

This fills that gap: it name-matches winner_name/loser_name to the players
table (last name + first initial, preferring ranked players on ties) and sets
match_date from the earliest point's IBM EpochTimeStart.

Usage (from backend/):
    python -m scrapers.ibm.link_players --prefix ibm-us_open-2026-
"""
import argparse
import asyncio

from sqlalchemy import text

from database import AsyncSessionLocal, engine


def parse_ibm_name(name: str) -> tuple[str, str] | None:
    """'J. Sinner' -> ('j', 'sinner'); 'A. de Minaur' -> ('a', 'de minaur')."""
    if not name:
        return None
    parts = name.strip().split()
    if len(parts) < 2:
        return None
    initial = parts[0].rstrip(".").lower()[:1]
    last = " ".join(parts[1:]).lower()
    return initial, last if initial and last else None


class Resolver:
    """Resolve an IBM '(initial, lastname)' to a player id.

    Primary key is (initial, full last name); a fallback keyed on the last
    token of the last name catches multi-word surnames that TML split into
    first/last differently (e.g. our 'Tomas Martin Etcheverry' -> last name
    'Martin Etcheverry' vs IBM 'T. Etcheverry'). Ranked players win ties;
    ambiguous fallback keys are dropped rather than guessed.
    """

    def __init__(self):
        self.exact: dict[tuple[str, str], tuple[str, bool]] = {}
        self.fallback: dict[tuple[str, str], str | None] = {}

    def _add(self, table, key, pid, ranked, allow_ambiguous):
        prev = table.get(key)
        if prev is None:
            table[key] = (pid, ranked)
        elif prev == "AMBIGUOUS":
            return
        elif ranked and not prev[1]:
            table[key] = (pid, ranked)  # ranked displaces unranked
        elif prev[1] == ranked and prev[0] != pid and not allow_ambiguous:
            table[key] = "AMBIGUOUS"  # two equally-ranked candidates -> give up

    def add(self, pid, first_name, last_name, ranked):
        initial = first_name[:1].lower()
        last = last_name.lower()
        self._add(self.exact, (initial, last), pid, ranked, allow_ambiguous=True)
        last_word = last.split()[-1] if last.split() else last
        if last_word != last:
            self._add(self.fallback, (initial, last_word), pid, ranked, allow_ambiguous=False)

    def get(self, key: tuple[str, str] | None) -> str | None:
        if not key:
            return None
        hit = self.exact.get(key)
        if isinstance(hit, tuple):
            return hit[0]
        fb = self.fallback.get(key)
        return fb[0] if isinstance(fb, tuple) else None


async def build_resolver(db) -> Resolver:
    rows = (await db.execute(text("""
        SELECT p.id, p.first_name, p.last_name,
               EXISTS (SELECT 1 FROM rankings r WHERE r.player_id = p.id) AS ranked
        FROM players p
        WHERE p.first_name IS NOT NULL AND p.last_name IS NOT NULL
    """))).all()
    resolver = Resolver()
    for r in rows:
        resolver.add(r.id, r.first_name, r.last_name, r.ranked)
    return resolver


async def link(prefix: str) -> None:
    async with AsyncSessionLocal() as db:
        resolver = await build_resolver(db)
        matches = (await db.execute(text("""
            SELECT id, winner_name, loser_name FROM matches
            WHERE id LIKE :prefix
              AND (winner_id IS NULL OR loser_id IS NULL OR match_date IS NULL)
        """), {"prefix": prefix + "%"})).all()

        # One grouped query for all match dates instead of one per match.
        date_rows = (await db.execute(text("""
            SELECT match_id, to_timestamp(MIN((raw_data->>'EpochTimeStart')::bigint))::date AS md
            FROM point_events
            WHERE match_id LIKE :prefix AND raw_data ? 'EpochTimeStart'
            GROUP BY match_id
        """), {"prefix": prefix + "%"})).all()
        date_by_id = {r.match_id: r.md for r in date_rows}

        params, linked_ids, dated, unresolved = [], 0, 0, 0
        for m in matches:
            w = parse_ibm_name(m.winner_name)
            l = parse_ibm_name(m.loser_name)
            wid = resolver.get(w) if w else None
            lid = resolver.get(l) if l else None
            md = date_by_id.get(m.id)
            params.append({"wid": wid, "lid": lid, "md": md, "mid": m.id})
            linked_ids += bool(wid and lid)
            unresolved += not (wid and lid)
            dated += bool(md)

        if params:
            await db.execute(text("""
                UPDATE matches SET
                    winner_id = COALESCE(:wid, winner_id),
                    loser_id  = COALESCE(:lid, loser_id),
                    match_date = COALESCE(:md, match_date)
                WHERE id = :mid
            """), params)  # asyncpg executemany — one round-trip
            await db.commit()

        print(f"{len(matches)} standalone matches: {linked_ids} fully ID-linked, "
              f"{dated} dated, {unresolved} with unresolved names")
    await engine.dispose()


async def _main():
    parser = argparse.ArgumentParser(description="Link standalone IBM matches to players")
    parser.add_argument("--prefix", required=True,
                        help="match-id prefix, e.g. ibm-us_open-2026-")
    args = parser.parse_args()
    await link(args.prefix)


if __name__ == "__main__":
    asyncio.run(_main())

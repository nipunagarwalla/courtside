"""Poll the ATP live-matches gateway for currently in-progress singles.

The gateway returns every match at active tournaments; we keep only
in-progress singles (Status == "P", not doubles) and cache a compact
summary in memory for the /api/live endpoint. No point-by-point stream —
just who is live and the current score.
"""
import asyncio

import requests
from sqlalchemy import text

from database import AsyncSessionLocal
from live import atp_live

LIVE_URL = "https://app.atptour.com/api/v2/gateway/livematches/website?scoringTournamentLevel"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.atptour.com/",
    "Origin": "https://www.atptour.com",
    "Accept": "application/json",
}


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _set_scores(player: dict) -> list[int]:
    """Per-set game counts (SetNumber 0 is a placeholder — skip it)."""
    out = []
    for s in player.get("Sets") or []:
        if s.get("SetNumber") and s.get("SetScore") is not None:
            out.append(int(s["SetScore"]))
    return out


def parse_live(payload: dict) -> list[dict]:
    """Extract in-progress singles matches from the gateway payload."""
    matches = []
    for t in payload.get("Data", {}).get("Tournaments") or []:
        event_id, year = t.get("EventId"), t.get("EventYear")
        tournament_id = f"{year}-{event_id}" if event_id and year else None
        for m in t.get("Matches") or []:
            if m.get("Status") != "P" or m.get("IsDoubles"):
                continue
            p1, p2 = m.get("PlayerTeam1") or {}, m.get("PlayerTeam2") or {}
            p1_sets, p2_sets = _set_scores(p1), _set_scores(p2)
            # sets won = completed sets where this player's game count is higher
            n = min(len(p1_sets), len(p2_sets))
            p1_won = sum(1 for i in range(n) if p1_sets[i] > p2_sets[i] and not (p1_sets[i] < 6 and p2_sets[i] < 6))
            p2_won = sum(1 for i in range(n) if p2_sets[i] > p1_sets[i] and not (p1_sets[i] < 6 and p2_sets[i] < 6))
            server = _to_int(m.get("LastServer"))
            round_ = (m.get("Round") or {}).get("ShortName")
            matches.append({
                "match_id": f"atp-{tournament_id}-{m.get('MatchId')}",
                "tournament_id": tournament_id,
                "tournament": t.get("EventDisplayName"),
                "round": round_,
                "surface": None,  # filled from DB in refresh
                "court": m.get("CourtName"),
                "p1_id": (p1.get("PlayerId") or "").upper() or None,
                "p1_name": f"{p1.get('PlayerFirstName', '')} {p1.get('PlayerLastName', '')}".strip(),
                "p1_country": p1.get("PlayerCountryCode"),
                "p2_id": (p2.get("PlayerId") or "").upper() or None,
                "p2_name": f"{p2.get('PlayerFirstName', '')} {p2.get('PlayerLastName', '')}".strip(),
                "p2_country": p2.get("PlayerCountryCode"),
                "score": {
                    "p1_sets": p1_won,
                    "p2_sets": p2_won,
                    "p1_games": p1_sets[-1] if p1_sets else 0,
                    "p2_games": p2_sets[-1] if p2_sets else 0,
                    "p1_game": p1.get("GamePointsPlayerTeam"),
                    "p2_game": p2.get("GamePointsPlayerTeam"),
                    "set_scores": list(zip(p1_sets, p2_sets)),
                    "server": server if server in (1, 2) else None,
                },
            })
    return matches


def fetch_live() -> list[dict]:
    r = requests.get(LIVE_URL, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return parse_live(r.json())


async def refresh_atp_live() -> int:
    """Fetch live matches, enrich surface from the tournaments table, cache them."""
    try:
        matches = await asyncio.to_thread(fetch_live)
    except Exception as e:
        print(f"ATP live poll error: {e}")
        return 0

    if matches:
        ids = {m["tournament_id"] for m in matches if m["tournament_id"]}
        async with AsyncSessionLocal() as db:
            rows = await db.execute(
                text("SELECT id, surface FROM tournaments WHERE id = ANY(:ids)"),
                {"ids": list(ids)},
            )
            surface_by_id = {r.id: r.surface for r in rows}
        for m in matches:
            m["surface"] = surface_by_id.get(m["tournament_id"])

    atp_live["matches"] = matches
    print(f"ATP live: {len(matches)} in-progress singles")
    return len(matches)

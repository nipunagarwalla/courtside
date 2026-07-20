"""Feature engineering for match-outcome prediction.

Two builders share the same feature definitions:

- `build_feature_row(match, db)` — async, point-in-time SQL per match.
  Used for serving (predict endpoint / upcoming matches): a handful of
  queries per call is fine.
- `DatasetBuilder` — a single chronological in-memory pass over all
  matches, maintaining rolling per-player state. Used for training:
  per-match SQL over ~200k matches against a remote DB would take hours;
  this takes seconds and computes identical point-in-time features.

Convention: p1 = match winner, p2 = loser at build time (training applies
a 50% symmetry swap afterwards so the model can't learn position bias).
"""
import math
from bisect import bisect_right
from collections import deque
from datetime import date, timedelta

from sqlalchemy import text

TIER_MAP = {
    "Grand Slam": 4, "Masters 1000": 3, "Masters": 3,
    "ATP 500": 2, "500": 2,
    "ATP 250": 1, "250": 1,
}

ROUND_MAP = {
    "R128": 1, "R64": 2, "R32": 3, "R16": 4,
    "QF": 5, "SF": 6, "F": 7,
}

FEATURE_COLUMNS = [
    "p1_rank", "p2_rank", "rank_diff", "p1_rank_log", "p2_rank_log",
    "points_ratio",
    "surface_hard", "surface_clay", "surface_grass",
    "p1_winrate_surface", "p2_winrate_surface", "surface_diff",
    "p1_form_last20", "p2_form_last20", "form_diff",
    "h2h_total", "p1_h2h_winrate",
    "tier_encoded", "round_encoded",
    "p1_days_rest", "p2_days_rest",
    "p1_age", "p2_age", "age_diff",
    "p1_first_serve_pct", "p2_first_serve_pct",
    "p1_bp_save_pct", "p2_bp_save_pct",
    "p1_ace_rate", "p2_ace_rate",
]

# Fallbacks when a value can't be computed. Serve-stat fallbacks are
# replaced by real tour medians (see tour_medians / DatasetBuilder).
DEFAULTS = {
    "rank": 300,
    "winrate": 0.5,
    "form": 0.5,
    "days_rest": 60,
    "age": 25.0,
    "first_serve_pct": 0.61,
    "bp_save_pct": 0.60,
    "ace_rate": 0.07,  # aces per service point (no per-game data in DB)
}

MAX_MISSING_FRACTION = 0.30

_MEDIANS_SQL = """
    SELECT
        percentile_cont(0.5) WITHIN GROUP (ORDER BY w_1stin::float / NULLIF(w_svpt, 0)) AS first_serve_pct,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY w_bpsaved::float / NULLIF(w_bpfaced, 0)) AS bp_save_pct,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY w_aces::float / NULLIF(w_svpt, 0)) AS ace_rate
    FROM matches
    WHERE w_svpt > 0
"""

_tour_medians: dict | None = None


async def tour_medians(db) -> dict:
    """Tour-wide serve-stat medians, cached for the process lifetime."""
    global _tour_medians
    if _tour_medians is None:
        row = (await db.execute(text(_MEDIANS_SQL))).first()
        _tour_medians = {
            "first_serve_pct": float(row.first_serve_pct or DEFAULTS["first_serve_pct"]),
            "bp_save_pct": float(row.bp_save_pct or DEFAULTS["bp_save_pct"]),
            "ace_rate": float(row.ace_rate or DEFAULTS["ace_rate"]),
        }
    return _tour_medians


def assemble(raw: dict, medians: dict) -> dict | None:
    """Turn raw (possibly-None) inputs into the final feature dict.

    Returns None when more than MAX_MISSING_FRACTION of the raw inputs
    are missing.
    """
    tracked = [
        "p1_rank", "p2_rank", "p1_points", "p2_points",
        "p1_winrate_surface", "p2_winrate_surface",
        "p1_form", "p2_form", "p1_days_rest", "p2_days_rest",
        "p1_age", "p2_age",
        "p1_first_serve_pct", "p2_first_serve_pct",
        "p1_bp_save_pct", "p2_bp_save_pct",
        "p1_ace_rate", "p2_ace_rate",
    ]
    missing = sum(1 for k in tracked if raw.get(k) is None)
    if missing / len(tracked) > MAX_MISSING_FRACTION:
        return None

    p1_rank = raw.get("p1_rank") or DEFAULTS["rank"]
    p2_rank = raw.get("p2_rank") or DEFAULTS["rank"]
    p1_pts, p2_pts = raw.get("p1_points"), raw.get("p2_points")
    points_ratio = (
        p1_pts / (p1_pts + p2_pts)
        if p1_pts is not None and p2_pts is not None and (p1_pts + p2_pts) > 0
        else 0.5
    )

    surface = (raw.get("surface") or "").lower()
    p1_ws = raw.get("p1_winrate_surface")
    p2_ws = raw.get("p2_winrate_surface")
    p1_ws = DEFAULTS["winrate"] if p1_ws is None else p1_ws
    p2_ws = DEFAULTS["winrate"] if p2_ws is None else p2_ws
    p1_form = raw.get("p1_form")
    p2_form = raw.get("p2_form")
    p1_form = DEFAULTS["form"] if p1_form is None else p1_form
    p2_form = DEFAULTS["form"] if p2_form is None else p2_form

    h2h_total = raw.get("h2h_total") or 0
    p1_h2h = raw.get("p1_h2h_winrate")
    p1_h2h = 0.5 if p1_h2h is None else p1_h2h

    p1_age = raw.get("p1_age") or DEFAULTS["age"]
    p2_age = raw.get("p2_age") or DEFAULTS["age"]

    def serve(prefix, stat):
        v = raw.get(f"{prefix}_{stat}")
        return medians[stat] if v is None else v

    p1_rest = raw.get("p1_days_rest")
    p2_rest = raw.get("p2_days_rest")

    return {
        "p1_rank": p1_rank,
        "p2_rank": p2_rank,
        "rank_diff": p1_rank - p2_rank,
        "p1_rank_log": math.log(p1_rank),
        "p2_rank_log": math.log(p2_rank),
        "points_ratio": points_ratio,
        "surface_hard": int(surface == "hard"),
        "surface_clay": int(surface == "clay"),
        "surface_grass": int(surface == "grass"),
        "p1_winrate_surface": p1_ws,
        "p2_winrate_surface": p2_ws,
        "surface_diff": p1_ws - p2_ws,
        "p1_form_last20": p1_form,
        "p2_form_last20": p2_form,
        "form_diff": p1_form - p2_form,
        "h2h_total": h2h_total,
        "p1_h2h_winrate": p1_h2h,
        "tier_encoded": TIER_MAP.get(raw.get("tier"), 0),
        "round_encoded": ROUND_MAP.get(raw.get("round"), 0),
        "p1_days_rest": min(p1_rest if p1_rest is not None else DEFAULTS["days_rest"], 60),
        "p2_days_rest": min(p2_rest if p2_rest is not None else DEFAULTS["days_rest"], 60),
        "p1_age": p1_age,
        "p2_age": p2_age,
        "age_diff": p1_age - p2_age,
        "p1_first_serve_pct": serve("p1", "first_serve_pct"),
        "p2_first_serve_pct": serve("p2", "first_serve_pct"),
        "p1_bp_save_pct": serve("p1", "bp_save_pct"),
        "p2_bp_save_pct": serve("p2", "bp_save_pct"),
        "p1_ace_rate": serve("p1", "ace_rate"),
        "p2_ace_rate": serve("p2", "ace_rate"),
    }


# ---------------------------------------------------------------------------
# Serving path: point-in-time SQL per player pair
# ---------------------------------------------------------------------------

async def _player_point_in_time(db, pid: str, surface: str, as_of: date) -> dict:
    rank_row = (await db.execute(text("""
        SELECT rank, points FROM rankings
        WHERE player_id = :pid AND ranking_type = 'standard' AND week_date <= :asof
        ORDER BY week_date DESC LIMIT 1
    """), {"pid": pid, "asof": as_of})).first()

    surf_row = (await db.execute(text("""
        SELECT COUNT(*) FILTER (WHERE winner_id = :pid) AS wins, COUNT(*) AS total
        FROM matches
        WHERE (winner_id = :pid OR loser_id = :pid)
          AND surface ILIKE :surface
          AND match_date < :asof AND match_date >= :asof3y
    """), {"pid": pid, "surface": surface, "asof": as_of,
           "asof3y": as_of - timedelta(days=3 * 365)})).first()

    form_row = (await db.execute(text("""
        SELECT COUNT(*) FILTER (WHERE winner_id = :pid) AS wins, COUNT(*) AS total,
               MAX(match_date) AS last_date
        FROM (
            SELECT winner_id, match_date FROM matches
            WHERE (winner_id = :pid OR loser_id = :pid) AND match_date < :asof
            ORDER BY match_date DESC LIMIT 20
        ) t
    """), {"pid": pid, "asof": as_of})).first()

    serve_row = (await db.execute(text("""
        SELECT AVG(fs) AS first_serve_pct, AVG(bps) AS bp_save_pct, AVG(ar) AS ace_rate
        FROM (
            SELECT
                CASE WHEN winner_id = :pid THEN w_1stin::float / NULLIF(w_svpt, 0)
                     ELSE l_1stin::float / NULLIF(l_svpt, 0) END AS fs,
                CASE WHEN winner_id = :pid THEN w_bpsaved::float / NULLIF(w_bpfaced, 0)
                     ELSE l_bpsaved::float / NULLIF(l_bpfaced, 0) END AS bps,
                CASE WHEN winner_id = :pid THEN w_aces::float / NULLIF(w_svpt, 0)
                     ELSE l_aces::float / NULLIF(l_svpt, 0) END AS ar
            FROM matches
            WHERE (winner_id = :pid OR loser_id = :pid)
              AND match_date < :asof AND w_svpt IS NOT NULL
            ORDER BY match_date DESC LIMIT 20
        ) t
    """), {"pid": pid, "asof": as_of})).first()

    dob = (await db.execute(
        text("SELECT dob FROM players WHERE id = :pid"), {"pid": pid}
    )).scalar()

    return {
        "rank": rank_row.rank if rank_row else None,
        "points": rank_row.points if rank_row else None,
        "winrate_surface": (surf_row.wins / surf_row.total) if surf_row and surf_row.total else None,
        "form": (form_row.wins / form_row.total) if form_row and form_row.total else None,
        "days_rest": (as_of - form_row.last_date).days if form_row and form_row.last_date else None,
        "age": (as_of - dob).days / 365.25 if dob else None,
        "first_serve_pct": float(serve_row.first_serve_pct) if serve_row and serve_row.first_serve_pct is not None else None,
        "bp_save_pct": float(serve_row.bp_save_pct) if serve_row and serve_row.bp_save_pct is not None else None,
        "ace_rate": float(serve_row.ace_rate) if serve_row and serve_row.ace_rate is not None else None,
    }


async def build_feature_row_for_pair(
    db, p1_id: str, p2_id: str, surface: str,
    tier: str | None, round_: str | None, as_of: date | None = None,
) -> dict | None:
    """Point-in-time features for an arbitrary player pair (serving path)."""
    as_of = as_of or date.today()
    medians = await tour_medians(db)

    p1 = await _player_point_in_time(db, p1_id, surface, as_of)
    p2 = await _player_point_in_time(db, p2_id, surface, as_of)

    h2h = (await db.execute(text("""
        SELECT COUNT(*) FILTER (WHERE winner_id = :p1) AS p1_wins, COUNT(*) AS total
        FROM matches
        WHERE ((winner_id = :p1 AND loser_id = :p2) OR (winner_id = :p2 AND loser_id = :p1))
          AND match_date < :asof
    """), {"p1": p1_id, "p2": p2_id, "asof": as_of})).first()

    raw = {
        "surface": surface, "tier": tier, "round": round_,
        "h2h_total": h2h.total if h2h else 0,
        "p1_h2h_winrate": (h2h.p1_wins / h2h.total) if h2h and h2h.total else None,
    }
    for prefix, p in (("p1", p1), ("p2", p2)):
        raw[f"{prefix}_rank"] = p["rank"]
        raw[f"{prefix}_points"] = p["points"]
        raw[f"{prefix}_winrate_surface"] = p["winrate_surface"]
        raw[f"{prefix}_form"] = p["form"]
        raw[f"{prefix}_days_rest"] = p["days_rest"]
        raw[f"{prefix}_age"] = p["age"]
        raw[f"{prefix}_first_serve_pct"] = p["first_serve_pct"]
        raw[f"{prefix}_bp_save_pct"] = p["bp_save_pct"]
        raw[f"{prefix}_ace_rate"] = p["ace_rate"]

    return assemble(raw, medians)


async def build_feature_row(match, db) -> dict | None:
    """Features for a match record (p1 = winner, p2 = loser)."""
    if not match.winner_id or not match.loser_id or not match.surface:
        return None
    return await build_feature_row_for_pair(
        db, match.winner_id, match.loser_id, match.surface,
        getattr(match, "tier", None), match.round,
        as_of=match.match_date or date.today(),
    )


# ---------------------------------------------------------------------------
# Training path: one chronological pass with rolling state
# ---------------------------------------------------------------------------

class DatasetBuilder:
    """Rolling per-player state; feed matches in match_date order."""

    def __init__(self, rankings: dict, dobs: dict, medians: dict):
        # rankings: pid -> (sorted [dates], [ranks], [points])
        self.rankings = rankings
        self.dobs = dobs
        self.medians = medians
        self.surface_hist: dict = {}   # (pid, surface) -> deque[(date, won)]
        self.form: dict = {}           # pid -> deque[bool] maxlen 20
        self.h2h: dict = {}            # frozenset({a,b}) -> {pid: wins}
        self.last_match: dict = {}     # pid -> date
        self.serve: dict = {}          # pid -> deque[(fs, bps, ar)] maxlen 20

    def _rank_at(self, pid, d):
        entry = self.rankings.get(pid)
        if not entry:
            return None, None
        dates, ranks, points = entry
        i = bisect_right(dates, d) - 1
        if i < 0:
            return None, None
        return ranks[i], points[i]

    def _surface_winrate(self, pid, surface, d):
        dq = self.surface_hist.get((pid, surface))
        if not dq:
            return None
        cutoff = d - timedelta(days=3 * 365)
        while dq and dq[0][0] < cutoff:
            dq.popleft()
        if not dq:
            return None
        return sum(1 for _, won in dq if won) / len(dq)

    def _serve_means(self, pid):
        dq = self.serve.get(pid)
        if not dq:
            return None, None, None
        def mean(idx):
            vals = [row[idx] for row in dq if row[idx] is not None]
            return sum(vals) / len(vals) if vals else None
        return mean(0), mean(1), mean(2)

    def features_for(self, m) -> dict | None:
        """Point-in-time features for match m (p1 = winner). Call BEFORE update()."""
        d = m.match_date
        w, l = m.winner_id, m.loser_id
        surface = (m.surface or "").lower()

        raw = {"surface": m.surface, "tier": m.tier, "round": m.round}
        pair = frozenset((w, l))
        h2h = self.h2h.get(pair)
        total = sum(h2h.values()) if h2h else 0
        raw["h2h_total"] = total
        raw["p1_h2h_winrate"] = (h2h.get(w, 0) / total) if total else None

        for prefix, pid in (("p1", w), ("p2", l)):
            rank, points = self._rank_at(pid, d)
            raw[f"{prefix}_rank"] = rank
            raw[f"{prefix}_points"] = points
            raw[f"{prefix}_winrate_surface"] = self._surface_winrate(pid, surface, d)
            form = self.form.get(pid)
            raw[f"{prefix}_form"] = (sum(form) / len(form)) if form else None
            last = self.last_match.get(pid)
            raw[f"{prefix}_days_rest"] = (d - last).days if last else None
            dob = self.dobs.get(pid)
            raw[f"{prefix}_age"] = (d - dob).days / 365.25 if dob else None
            fs, bps, ar = self._serve_means(pid)
            raw[f"{prefix}_first_serve_pct"] = fs
            raw[f"{prefix}_bp_save_pct"] = bps
            raw[f"{prefix}_ace_rate"] = ar

        return assemble(raw, self.medians)

    def update(self, m):
        """Fold match m into the rolling state (call AFTER features_for)."""
        d = m.match_date
        w, l = m.winner_id, m.loser_id
        surface = (m.surface or "").lower()

        for pid, won in ((w, True), (l, False)):
            self.surface_hist.setdefault((pid, surface), deque()).append((d, won))
            self.form.setdefault(pid, deque(maxlen=20)).append(won)
            self.last_match[pid] = d

        pair = frozenset((w, l))
        self.h2h.setdefault(pair, {})[w] = self.h2h.setdefault(pair, {}).get(w, 0) + 1

        def ratio(a, b):
            return (a / b) if a is not None and b else None

        for pid, svpt, stin, aces, bps, bpf in (
            (w, m.w_svpt, m.w_1stin, m.w_aces, m.w_bpsaved, m.w_bpfaced),
            (l, m.l_svpt, m.l_1stin, m.l_aces, m.l_bpsaved, m.l_bpfaced),
        ):
            if svpt:
                self.serve.setdefault(pid, deque(maxlen=20)).append((
                    ratio(stin, svpt), ratio(bps, bpf), ratio(aces, svpt),
                ))

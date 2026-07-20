"""Parser for IBM SlamTracker history feeds (plain JSON flat array).

Same player-number convention as the Infosys parser: player 1 in stored
rows is always OUR match winner. IBM's own P1/P2 order is arbitrary, so
callers pass winner_is_p1=False to flip when IBM's P2 won the match.

Real-schema notes (verified against US Open 2025):
- There are no P1Name/P2Name fields; names appear only in Sentence text.
- P1Score/P2Score are the score AFTER the point, so score_before is
  reconstructed from the previous point of the same game.
- SetWinner/MatchWinner mark the set-/match-deciding point.
"""
import json
import re

_NAME_RE = re.compile(r"([A-Z]\.\s?[A-Za-z'\-\.]+(?:\s[A-Za-z'\-\.]+)*?)\s(wins|loses)\s")


def _numeric_points(data: list[dict]):
    for point in data:
        try:
            yield int(point.get("PointNumber", "")), point
        except (TypeError, ValueError):
            continue  # skip pre-match events like "0X"/"0Y"


def match_winner_team(data: list[dict]) -> int | None:
    """1 or 2 from the last point's MatchWinner flag, else None (in progress)."""
    for _, point in reversed(list(_numeric_points(data))):
        mw = point.get("MatchWinner", "0")
        if mw in ("1", "2"):
            return int(mw)
        break
    return None


def extract_player_names(data: list[dict]) -> dict[int, str]:
    """Map IBM team number -> display name, parsed from point sentences."""
    names: dict[int, str] = {}
    for _, point in _numeric_points(data):
        sentence = point.get("Sentence") or ""
        m = _NAME_RE.search(sentence)
        if not m:
            continue
        try:
            winner = int(point.get("PointWinner", "0"))
        except (TypeError, ValueError):
            continue
        if winner not in (1, 2):
            continue
        team = winner if m.group(2) == "wins" else 3 - winner
        names.setdefault(team, m.group(1))
        if len(names) == 2:
            break
    return names


def parse_ibm_points(data: list[dict], our_match_id: str,
                     winner_is_p1: bool = True) -> list[dict]:
    """Parse IBM flat point array into point_events rows."""

    def flip(n):
        if not winner_is_p1 and n in (1, 2):
            return 3 - n
        return n

    def pair(point, f1, f2):
        a, b = point.get(f1), point.get(f2)
        return (b, a) if not winner_is_p1 else (a, b)

    rows = []
    prev_score = {}  # (set, game) -> score_after of previous point
    for pn_int, point in _numeric_points(data):

        def flag(f):
            return point.get(f, "0") != "0"

        def to_int(f):
            try:
                return int(point[f]) if point.get(f) not in (None, "") else None
            except (TypeError, ValueError):
                return None

        def parse_dist(s):
            try:
                return float(s.split(",")[0])
            except (AttributeError, ValueError, IndexError):
                return None

        end_type = (
            "Ace"            if flag("Ace")           else
            "Double Fault"   if flag("DoubleFault")   else
            "Winner"         if flag("Winner")        else
            "Unforced Error" if flag("UnforcedError") else
            "Forced Error"
        )

        set_no, game_no = to_int("SetNo"), to_int("GameNo")
        s1, s2 = pair(point, "P1Score", "P2Score")
        score_after = f"{s1 or '0'}-{s2 or '0'}"
        score_before = prev_score.get((set_no, game_no), "0-0")
        prev_score[(set_no, game_no)] = score_after

        g1, g2 = pair(point, "P1GamesWon", "P2GamesWon")
        st1, st2 = pair(point, "P1SetsWon", "P2SetsWon")
        d1, d2 = pair(point, "P1DistanceRun", "P2DistanceRun")
        shot = point.get("WinnerShotType")

        def as_int(v):
            try:
                return int(v)
            except (TypeError, ValueError):
                return None

        rows.append({
            "match_id":        our_match_id,
            "set_number":      set_no,
            "game_number":     game_no,
            "point_number":    pn_int,
            "server":          flip(to_int("PointServer")),
            "score_before":    score_before,
            "score_after":     score_after,
            "p1_games":        as_int(g1),
            "p2_games":        as_int(g2),
            "p1_sets":         as_int(st1),
            "p2_sets":         as_int(st2),
            "winner":          flip(to_int("PointWinner")),
            "point_end_type":  end_type,
            "serve_speed_kmh": to_int("Speed_KMH") or None,
            "serve_type":      {1: "1st", 2: "2nd"}.get(to_int("ServeNumber")),
            "rally_length":    to_int("RallyCount") or None,
            "is_break_point":  flag("BreakPoint"),
            "is_game_winner":  flag("GameWinner"),
            "is_set_point":    flag("SetWinner"),    # set-deciding point (real IBM flag)
            "is_match_point":  flag("MatchWinner"),  # match-deciding point (real IBM flag)
            "winner_shot":     shot if shot not in (None, "", "0") else None,
            "serve_width":     point.get("ServeWidth") or None,
            "serve_depth":     point.get("ServeDepth") or None,
            "return_depth":    point.get("ReturnDepth") or None,
            "p1_distance_m":   parse_dist(d1),
            "p2_distance_m":   parse_dist(d2),
            "sentence":        point.get("Sentence") or None,
            "source":          "ibm",
            "raw_data":        json.dumps(point),
        })
    return rows

"""Parsers for decrypted Infosys payloads.

Player-number convention: in everything we store, player 1 is OUR match
winner and player 2 is our match loser. Infosys team order (tm1/tm2) is
arbitrary relative to that, so parsers take a `swap` flag — computed by
`needs_swap()` — that flips 1<->2 when Infosys tm2 is our winner.
"""
import json

RESULT_LABELS = {
    "A": "Ace",
    "DF": "Double Fault",
    "W": "Winner",
    "UE": "Unforced Error",
    "FE": "Forced Error",
}


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _flip(n: int | None, swap: bool) -> int | None:
    if swap and n in (1, 2):
        return 3 - n
    return n


def infosys_player_ids(match_beats: dict) -> tuple[str | None, str | None]:
    """(tm1 player id, tm2 player id), uppercased."""
    pd = match_beats.get("playerData") or {}
    t1, t2 = pd.get("tm1Ply1Id"), pd.get("tm2Ply1Id")
    return (t1.upper() if t1 else None, t2.upper() if t2 else None)


def matches_our_players(match_beats: dict, winner_id: str, loser_id: str) -> bool:
    t1, t2 = infosys_player_ids(match_beats)
    if not t1 or not t2:
        return False
    return {t1, t2} == {winner_id.upper(), loser_id.upper()}


def needs_swap(match_beats: dict, winner_id: str) -> bool:
    """True when Infosys tm2 is our match winner (so 1<->2 must flip)."""
    _, t2 = infosys_player_ids(match_beats)
    return t2 == winner_id.upper()


def compute_set_and_match_point(
    p1_score: str, p2_score: str,
    p1_games: int, p2_games: int,
    p1_sets: int, p2_sets: int,
    total_sets_needed: int,
    is_tiebreak: bool = False,
) -> tuple[bool, bool]:
    """Compute set/match point from the score BEFORE a point is played.

    A point is a set point when the leading player is one point from taking
    the set; a match point when taking that set would win the match
    (total_sets_needed = 2 for best-of-3, 3 for best-of-5).
    """
    if is_tiebreak:
        # Tiebreak scores are numeric; set point at >=6 with a lead
        try:
            t1, t2 = int(p1_score), int(p2_score)
        except (TypeError, ValueError):
            return False, False
        p1_at_sp = t1 >= 6 and t1 > t2
        p2_at_sp = t2 >= 6 and t2 > t1
    else:
        # Game point: at 40 with opponent below 40, or at advantage
        p1_at_gp = (p1_score == "40" and p2_score not in ("40", "AD")) or p1_score == "AD"
        p2_at_gp = (p2_score == "40" and p1_score not in ("40", "AD")) or p2_score == "AD"
        p1_at_sp = p1_at_gp and p1_games >= 5 and p1_games > p2_games
        p2_at_sp = p2_at_gp and p2_games >= 5 and p2_games > p1_games

    is_set_point = p1_at_sp or p2_at_sp
    is_match_point = False
    if p1_at_sp:
        is_match_point = (p1_sets + 1) >= total_sets_needed
    elif p2_at_sp:
        is_match_point = (p2_sets + 1) >= total_sets_needed
    return is_set_point, is_match_point


def _player_names(match_beats: dict, swap: bool) -> dict[int, str]:
    pd = match_beats.get("playerData") or {}
    n1 = pd.get("tm1Ply1Name") or "Player 1"
    n2 = pd.get("tm2Ply1Name") or "Player 2"
    if swap:
        n1, n2 = n2, n1
    return {1: n1, 2: n2}


def parse_match_beats(
    match_beats: dict, our_match_id: str, swap: bool,
    total_sets_needed: int = 2,
) -> list[dict]:
    """Flatten setData -> gameData -> pointData into point_events rows."""
    names = _player_names(match_beats, swap)
    rows = []
    sets_won = {1: 0, 2: 0}

    for set_data in match_beats.get("setData") or []:
        set_number = set_data.get("set")
        games_won = {1: 0, 2: 0}

        for game in set_data.get("gameData") or []:
            game_number = game.get("game")
            is_tiebreak = bool(game.get("isTieBreak"))
            point_data = game.get("pointData") or []
            prev_score = "0-0"

            for idx, p in enumerate(point_data):
                server = _flip(_to_int(p.get("server")), swap)
                winner = _flip(_to_int(p.get("scorer")), swap)
                s1, s2 = p.get("tm1GameScore"), p.get("tm2GameScore")
                if swap:
                    s1, s2 = s2, s1
                score_after = f"{s1}-{s2}"
                rally = (p.get("tm1Rally") or 0) + (p.get("tm2Rally") or 0)
                speed = p.get("serveSpeed")
                result = p.get("result")
                end_type = RESULT_LABELS.get(result, result)
                stroke = p.get("stroke")
                is_last_point = idx == len(point_data) - 1
                sentence = None
                if winner in names:
                    sentence = f"{names[winner]} wins the point ({end_type}) — {score_after}"

                before_p1, _, before_p2 = prev_score.partition("-")
                is_set_point, is_match_point = compute_set_and_match_point(
                    before_p1, before_p2,
                    games_won[1], games_won[2],
                    sets_won[1], sets_won[2],
                    total_sets_needed, is_tiebreak,
                )

                rows.append({
                    "match_id": our_match_id,
                    "set_number": set_number,
                    "game_number": game_number,
                    "point_number": p.get("point"),
                    "server": server,
                    "score_before": prev_score,
                    "score_after": score_after,
                    "p1_games": games_won[1],
                    "p2_games": games_won[2],
                    "p1_sets": sets_won[1],
                    "p2_sets": sets_won[2],
                    "winner": winner,
                    "point_end_type": end_type,
                    "serve_speed_kmh": int(speed) if speed else None,
                    "serve_type": {1: "1st", 2: "2nd"}.get(p.get("serve")),
                    "rally_length": rally or None,
                    "is_break_point": bool(p.get("isBrkPt")),
                    "is_set_point": is_set_point or bool(p.get("isCspPt")),
                    "is_match_point": is_match_point,
                    "is_game_winner": is_last_point,
                    "winner_shot": stroke if stroke and stroke != "N" else None,
                    "sentence": sentence,
                    "source": "infosys",
                    "raw_data": json.dumps(p),
                })
                prev_score = score_after

            game_winner = _flip(_to_int(game.get("gameWinner")), swap)
            if game_winner in games_won:
                games_won[game_winner] += 1

        set_winner = _flip(_to_int(set_data.get("setWinner")), swap)
        if set_winner in sets_won:
            sets_won[set_winner] += 1

    return rows


def parse_keystats(keystats: dict, our_match_id: str, swap: bool) -> list[dict]:
    """Flatten setStats into match_keystats rows. set 0 = whole match."""
    rows = []
    for set_key, stats in (keystats.get("setStats") or {}).items():
        set_number = _to_int(set_key.removeprefix("set"))
        if set_number is None:
            continue
        for stat in stats or []:
            name = stat.get("name")
            if not name:
                continue
            v1, v2 = stat.get("player1"), stat.get("player2")
            if swap:
                v1, v2 = v2, v1
            for player, value in ((1, v1), (2, v2)):
                if value is None or value == "":
                    continue
                rows.append({
                    "match_id": our_match_id,
                    "set_number": set_number,
                    "player": player,
                    "stat_name": name,
                    "value": str(value),
                })
    return rows

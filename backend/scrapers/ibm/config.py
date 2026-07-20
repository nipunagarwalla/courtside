from datetime import date

IBM_CONFIG = {
    "us_open": {
        "base_url":        "https://www.usopen.org",
        "feeds_path":      "/en_US/scores/feeds/{year}/slamtracker",
        "years":           [2025, 2026],
        "enabled":         True,
        "tournament_name": "US Open",
        "surface":         "Hard",
    },
    "wimbledon": {
        "base_url":        "https://www.wimbledon.com",
        "feeds_path":      "/en_GB/scores/feeds/{year}/slamtracker",
        "years":           [2026],
        "enabled":         False,  # endpoint not yet verified — enable after sniffing
        "tournament_name": "Wimbledon",
        "surface":         "Grass",
    },
}

IBM_TOURNAMENT_WINDOWS = [
    {"key": "us_open",   "start": date(2026, 8, 24), "end": date(2026, 9, 6)},
    {"key": "wimbledon", "start": date(2027, 6, 28), "end": date(2027, 7, 11)},
]

# matches per round in a 128 draw; round digit -> match count
ROUNDS = {1: 64, 2: 32, 3: 16, 4: 8, 5: 4, 6: 2, 7: 1}

# round digit -> our matches.round value (128-player singles draw)
ROUND_NAMES = {1: "R128", 2: "R64", 3: "R32", 4: "R16", 5: "QF", 6: "SF", 7: "F"}


def ibm_headers(tournament_key: str) -> dict:
    origin = IBM_CONFIG[tournament_key]["base_url"]
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": origin + "/",
        "Origin": origin,
        "Accept": "application/json",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
    }


def all_match_ids(draws: list[int] | None = None) -> list[str]:
    """
    Format: {draw}{round}{match_nn}
    draw:  1=MS 2=WS 3=MD 4=WD 5=XD
    round: 1=R1 2=R2 3=R3 4=R4 5=QF 6=SF 7=F
    """
    ids = []
    for draw in draws or range(1, 6):
        for round_ in range(1, 8):
            for match in range(1, ROUNDS[round_] + 1):
                ids.append(f"{draw}{round_}{match:02d}")
    return ids


def is_tournament_active() -> str | None:
    today = date.today()
    for t in IBM_TOURNAMENT_WINDOWS:
        cfg = IBM_CONFIG.get(t["key"], {})
        if cfg.get("enabled") and t["start"] <= today <= t["end"]:
            return t["key"]
    return None

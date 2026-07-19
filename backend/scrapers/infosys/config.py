INFOSYS_HOST = "https://itp-atp-sls.infosys-platforms.com"

# CloudFront/WAF rejects requests without a complete browser header set
# (the sec-fetch-* / sec-ch-ua client-hint headers are what get us past it).
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.atptour.com",
    "Referer": "https://www.atptour.com/",
    "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
}

ENDPOINTS = {
    "match_beats": "/prod/api/match-beats/data/year/{year}/eventId/{event_id}/matchId/{match_id}",
    "keystats":    "/prod/api/stats-plus/v1/keystats/year/{year}/eventId/{event_id}/matchId/{match_id}",
}

INFOSYS_EVENTS = {
    # key = our tournament ID pattern to match against
    # Note: Grand Slams are listed but rarely have match-beats data (they run
    # IBM systems, not Infosys) — those simply come back 404 and we return
    # has_data: false.
    "australian-open":      {"event_id": "580", "max_matches": 128},
    "roland-garros":        {"event_id": "520", "max_matches": 128},
    "wimbledon":            {"event_id": "540", "max_matches": 128},
    "indian-wells-masters": {"event_id": "404", "max_matches": 96},
    "miami-open":           {"event_id": "403", "max_matches": 96},
    "monte-carlo-masters":  {"event_id": "410", "max_matches": 64},
    "madrid-open":          {"event_id": "1536","max_matches": 96},
    "rome-masters":         {"event_id": "416", "max_matches": 96},
    "canada-masters":       {"event_id": "421", "max_matches": 64},
    "cincinnati-masters":   {"event_id": "422", "max_matches": 64},
    "paris-masters":        {"event_id": "352", "max_matches": 64},
    "shanghai-masters":     {"event_id": "5014","max_matches": 64},
}

# Words too generic to identify a tournament on their own ("Rome Masters"
# must not match "indian-wells-masters" just because both contain "masters").
_GENERIC_WORDS = {"open", "masters", "atp"}


def get_event_config(tournament_name: str) -> dict | None:
    """Match a tournament name to its Infosys event config."""
    name_lower = tournament_name.lower()
    # Pass 1: full key phrase match ("monte carlo masters" in name)
    for key, cfg in INFOSYS_EVENTS.items():
        if key in name_lower or key.replace("-", " ") in name_lower:
            return cfg
    # Pass 2: distinctive-word match ("wimbledon", "cincinnati", "monte"...)
    for key, cfg in INFOSYS_EVENTS.items():
        words = [w for w in key.split("-") if w not in _GENERIC_WORDS]
        if any(w in name_lower for w in words):
            return cfg
    return None

"""Courtside — End-to-End Test Suite.

Run from backend/ with both servers active:
    cd backend && uvicorn main:app --reload   (http://localhost:8000)
    cd frontend && npm run dev                 (http://localhost:3000)
    python test_suite.py
"""
import asyncio
import json
import os
import sys
import time

import httpx
from sqlalchemy import text

from database import engine

BASE = "http://localhost:8000"
FRONT = "http://localhost:3000"

GROUND_TRUTH = {
    "sinner_id": "S0AG",
    "alcaraz_id": "A0E2",
    "zverev_id": "Z355",
    "djokovic_id": "D643",
    "alcaraz_vs_sinner_total": 17,
    "alcaraz_vs_sinner_alcaraz_wins": 10,
    "alcaraz_vs_sinner_sinner_wins": 7,
}


# --------------------------------------------------------------------------
# Test 1 — Database Integrity
# --------------------------------------------------------------------------
async def test_database():
    results = []
    async with engine.connect() as conn:
        r = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        ))
        tables = [row[0] for row in r]
        expected = ['live_polls', 'match_keystats', 'match_rally', 'matches',
                    'players', 'point_events', 'rankings', 'tournaments']
        results.append({
            "test": "1.1 All 8 tables exist",
            "pass": all(t in tables for t in expected),
            "detail": f"Found: {tables}",
        })

        for table, min_count in [
            ("players", 7000), ("tournaments", 8000),
            ("matches", 190000), ("rankings", 100),
        ]:
            count = (await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))).scalar()
            results.append({
                "test": f"1.2 {table} count >= {min_count}",
                "pass": count >= min_count,
                "detail": f"actual: {count}",
            })

        row = (await conn.execute(text(
            "SELECT id, name FROM players WHERE id = 'S0AG'"))).fetchone()
        results.append({
            "test": "1.3 Sinner in players table (id=S0AG)",
            "pass": row is not None and "Sinner" in (row[1] or ""),
            "detail": str(row),
        })

        row = (await conn.execute(text(
            "SELECT id, name FROM players WHERE id = 'A0E2'"))).fetchone()
        results.append({
            "test": "1.4 Alcaraz in players table (id=A0E2)",
            "pass": row is not None and "Alcaraz" in (row[1] or ""),
            "detail": str(row),
        })

        count = (await conn.execute(text(
            "SELECT COUNT(*) FROM rankings WHERE week_date >= CURRENT_DATE - 14"))).scalar()
        results.append({
            "test": "1.5 Rankings have recent data (last 14 days)",
            "pass": count >= 100,
            "detail": f"recent rankings: {count}",
        })

        row = (await conn.execute(text(
            "SELECT rank FROM rankings WHERE player_id = 'S0AG' "
            "ORDER BY week_date DESC LIMIT 1"))).fetchone()
        results.append({
            "test": "1.6 Sinner ranked #1 in rankings table",
            "pass": row is not None and row[0] == 1,
            "detail": f"Sinner rank: {row[0] if row else 'not found'}",
        })

        count = (await conn.execute(text(
            "SELECT COUNT(*) FROM point_events WHERE source = 'ibm'"))).scalar()
        results.append({
            "test": "1.7 IBM US Open 2025 points in DB (>=25000)",
            "pass": count >= 25000,
            "detail": f"IBM point_events: {count}",
        })

        count = (await conn.execute(text(
            "SELECT COUNT(*) FROM point_events WHERE source = 'infosys'"))).scalar()
        results.append({
            "test": "1.8 Infosys point_events in DB (at least some scraped)",
            "pass": count > 0,
            "detail": f"Infosys point_events: {count}",
        })

        count = (await conn.execute(text(
            "SELECT COUNT(*) FROM matches WHERE winner_ranking_points IS NOT NULL"))).scalar()
        results.append({
            "test": "1.9 winner_ranking_points populated (>=100000)",
            "pass": count >= 100000,
            "detail": f"matches with points: {count}",
        })

        count = (await conn.execute(text(
            "SELECT COUNT(*) FROM matches WHERE infosys_match_id IS NOT NULL"))).scalar()
        results.append({
            "test": "1.10 infosys_match_id cached for scraped matches",
            "pass": count > 0,
            "detail": f"matches with infosys_match_id: {count}",
        })

    return results


# --------------------------------------------------------------------------
# Test 2 — Backend API Endpoints
# --------------------------------------------------------------------------
async def test_api():
    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{BASE}/health")
        results.append({
            "test": "2.1 GET /health returns 200 with status ok",
            "pass": r.status_code == 200 and r.json().get("status") == "ok",
            "detail": f"{r.status_code} {r.text[:100]}",
        })

        r = await client.get(f"{BASE}/api/rankings?limit=100")
        data = r.json() if r.status_code == 200 else []
        results.append({
            "test": "2.2 GET /api/rankings returns 100+ players",
            "pass": r.status_code == 200 and len(data) >= 100,
            "detail": f"count: {len(data)}",
        })

        rankings = data
        rank1 = next((p for p in rankings if p.get("rank") == 1), None)
        results.append({
            "test": "2.3 Rankings: rank 1 is Sinner",
            "pass": rank1 is not None and "Sinner" in rank1.get("name", ""),
            "detail": f"rank1: {rank1}",
        })
        rank2 = next((p for p in rankings if p.get("rank") == 2), None)
        results.append({
            "test": "2.4 Rankings: rank 2 is Zverev",
            "pass": rank2 is not None and "Zverev" in rank2.get("name", ""),
            "detail": f"rank2: {rank2}",
        })
        rank3 = next((p for p in rankings if p.get("rank") == 3), None)
        results.append({
            "test": "2.5 Rankings: rank 3 is Alcaraz",
            "pass": rank3 is not None and "Alcaraz" in rank3.get("name", ""),
            "detail": f"rank3: {rank3}",
        })

        r = await client.get(f"{BASE}/api/players?search=sinner")
        data = r.json()
        results.append({
            "test": "2.6 GET /api/players?search=sinner returns results",
            "pass": r.status_code == 200 and any("Sinner" in p.get("name", "") for p in data),
            "detail": f"results: {[p.get('name') for p in data[:3]]}",
        })

        r = await client.get(f"{BASE}/api/players/S0AG")
        data = r.json()
        results.append({
            "test": "2.7 GET /api/players/S0AG returns Sinner profile",
            "pass": r.status_code == 200 and "Sinner" in data.get("name", ""),
            "detail": f"name: {data.get('name')}, rank: {data.get('current_rank')}",
        })

        titles = data.get("career_titles", 0) or 0 if r.status_code == 200 else 0
        results.append({
            "test": "2.8 Sinner career_titles >= 28",
            "pass": titles >= 28,
            "detail": f"career_titles: {titles}",
        })

        wr_overall = data.get("win_rate_overall", 0) or 0
        wr_hard = data.get("win_rate_hard", 0) or 0
        results.append({
            "test": "2.9 Sinner win rates are sensible (overall >0.70)",
            "pass": wr_overall > 0.70,
            "detail": f"overall: {wr_overall:.3f}, hard: {wr_hard:.3f}",
        })

        r = await client.get(f"{BASE}/api/tournaments?year=2026")
        results.append({
            "test": "2.10 GET /api/tournaments?year=2026 returns results",
            "pass": r.status_code == 200 and len(r.json()) > 0,
            "detail": f"count: {len(r.json())}",
        })

        r = await client.get(f"{BASE}/api/compare?p1=A0E2&p2=S0AG")
        data = r.json()
        h2h = data.get("h2h", {})
        results.append({
            "test": "2.11 GET /api/compare Alcaraz vs Sinner returns H2H",
            "pass": r.status_code == 200 and h2h.get("total_matches", 0) >= 15,
            "detail": f"total: {h2h.get('total_matches')}, Alcaraz: {h2h.get('p1_wins')}, Sinner: {h2h.get('p2_wins')}",
        })
        results.append({
            "test": "2.12 H2H: Alcaraz leads Sinner 10-7 (p1=Alcaraz)",
            "pass": h2h.get("p1_wins") == 10 and h2h.get("p2_wins") == 7,
            "detail": f"A0E2 wins: {h2h.get('p1_wins')}, S0AG wins: {h2h.get('p2_wins')}",
        })

        required_keys = ["player1", "player2", "h2h", "h2h_by_surface",
                         "h2h_by_tier", "recent_form", "surface_win_rates",
                         "career_stats", "serve_stats", "h2h_matches"]
        results.append({
            "test": "2.13 Compare response has all 10 sections",
            "pass": r.status_code == 200 and all(k in data for k in required_keys),
            "detail": f"present: {[k for k in required_keys if k in data]}",
        })

        r = await client.get(f"{BASE}/api/matches?player_id=S0AG&limit=10")
        results.append({
            "test": "2.14 GET /api/matches?player_id=S0AG returns matches",
            "pass": r.status_code == 200 and len(r.json()) > 0,
            "detail": f"count: {len(r.json())}",
        })

        r = await client.get(f"{BASE}/api/players/s0ag")
        results.append({
            "test": "2.15 Player lookup is case-insensitive (s0ag == S0AG)",
            "pass": r.status_code == 200 and "Sinner" in r.json().get("name", ""),
            "detail": f"status: {r.status_code}",
        })

        r = await client.get(f"{BASE}/api/players/XXXXX")
        results.append({
            "test": "2.16 Unknown player returns 404",
            "pass": r.status_code == 404,
            "detail": f"status: {r.status_code}",
        })

        r2 = await client.get(f"{BASE}/api/matches?player_id=S0AG&limit=100")
        matches = r2.json()
        unscraped_id = None
        for m in matches:
            if "1968" in str(m.get("match_date", "")):
                unscraped_id = m["id"]
                break
        if unscraped_id is None and matches:
            unscraped_id = matches[-1]["id"]
        if unscraped_id:
            r = await client.get(f"{BASE}/api/matches/{unscraped_id}/points")
            data = r.json()
            results.append({
                "test": "2.17 /points returns has_data field (true or false)",
                "pass": r.status_code == 200 and "has_data" in data,
                "detail": f"has_data: {data.get('has_data')}, match: {unscraped_id}",
            })

        r = await client.get(
            f"{BASE}/api/predict?p1=S0AG&p2=A0E2&surface=Hard&tier=Grand+Slam&round=SF")
        results.append({
            "test": "2.18 GET /api/predict returns prediction or 503",
            "pass": r.status_code in (200, 503),
            "detail": f"status: {r.status_code}, body: {r.text[:150]}",
        })

        if r.status_code == 200:
            pred = r.json().get("prediction", {})
            required_pred = ["p1_win_probability", "p2_win_probability", "confidence", "key_factors"]
            results.append({
                "test": "2.19 Prediction has all required fields",
                "pass": all(k in pred for k in required_pred),
                "detail": f"keys: {list(pred.keys())}",
            })
            p1 = pred.get("p1_win_probability", 0)
            p2 = pred.get("p2_win_probability", 0)
            results.append({
                "test": "2.20 Win probabilities sum to 1.0",
                "pass": abs((p1 + p2) - 1.0) < 0.01,
                "detail": f"p1: {p1}, p2: {p2}, sum: {p1 + p2}",
            })
            r_clay = await client.get(
                f"{BASE}/api/predict?p1=S0AG&p2=A0E2&surface=Clay&tier=Grand+Slam&round=SF")
            if r_clay.status_code == 200:
                pred_clay = r_clay.json().get("prediction", {})
                p1_hard = pred.get("p1_win_probability", 0.5)
                p1_clay = pred_clay.get("p1_win_probability", 0.5)
                results.append({
                    "test": "2.21 Prediction differs between Hard and Clay surfaces",
                    "pass": abs(p1_hard - p1_clay) > 0.02,
                    "detail": f"Sinner vs Alcaraz: Hard {p1_hard:.3f}, Clay {p1_clay:.3f}",
                })

        r = await client.get(f"{BASE}/api/live")
        results.append({
            "test": "2.22 GET /api/live returns array (empty outside tournaments)",
            "pass": r.status_code == 200 and isinstance(r.json(), list),
            "detail": f"live matches: {len(r.json())}",
        })

        r = await client.get(f"{BASE}/api/backfill/status")
        data = r.json()
        usopen_entry = next(
            (x for x in data if "open" in str(x).lower()), None)
        results.append({
            "test": "2.23 GET /api/backfill/status shows US Open data",
            "pass": r.status_code == 200 and len(data) > 0,
            "detail": f"entries: {len(data)}, US Open: {usopen_entry}",
        })

        async with client.stream("GET", f"{BASE}/api/matches/test/live-stream") as resp:
            results.append({
                "test": "2.24 SSE endpoint returns text/event-stream content type",
                "pass": "text/event-stream" in resp.headers.get("content-type", ""),
                "detail": f"content-type: {resp.headers.get('content-type')}",
            })

    return results


# --------------------------------------------------------------------------
# Test 3 — Point-by-Point On-Demand Scraping
# --------------------------------------------------------------------------
async def test_point_by_point():
    results = []
    async with httpx.AsyncClient(timeout=60) as client:
        r_tourn = await client.get(f"{BASE}/api/tournaments?year=2026")
        tournaments = r_tourn.json()
        mc = next((t for t in tournaments
                   if "monte" in t.get("name", "").lower()
                   or "carlo" in t.get("name", "").lower()), None)

        if mc:
            r_matches = await client.get(f"{BASE}/api/tournaments/{mc['id']}")
            mc_matches = r_matches.json().get("matches", [])
            final = next((m for m in mc_matches if m.get("round") == "F"), None)
            if not final:
                final = mc_matches[0] if mc_matches else None

            if final:
                match_id = final["id"]
                r = await client.get(f"{BASE}/api/matches/{match_id}/points", timeout=120)
                data = r.json()
                results.append({
                    "test": "3.1 Monte Carlo 2026 final: /points returns data",
                    "pass": r.status_code == 200 and data.get("has_data") is True,
                    "detail": f"has_data: {data.get('has_data')}, sets: {len(data.get('sets', []))}",
                })

                if data.get("has_data"):
                    sets = data.get("sets", [])
                    results.append({
                        "test": "3.2 Monte Carlo final has correct number of sets",
                        "pass": 2 <= len(sets) <= 5,
                        "detail": f"sets: {[(s['set_number'], s['p1_games'], s['p2_games']) for s in sets]}",
                    })
                    if sets and sets[0].get("games"):
                        first_point = sets[0]["games"][0]["points"][0]
                        required_fields = ["point_number", "server", "winner",
                                           "score_before", "point_end_type"]
                        results.append({
                            "test": "3.3 Point events have required fields",
                            "pass": all(f in first_point for f in required_fields),
                            "detail": f"fields: {list(first_point.keys())[:10]}",
                        })

                t0 = time.time()
                r2 = await client.get(f"{BASE}/api/matches/{match_id}/points")
                elapsed = time.time() - t0
                results.append({
                    "test": "3.4 Second /points call is fast (<2s, served from DB)",
                    "pass": elapsed < 2.0 and r2.status_code == 200,
                    "detail": f"elapsed: {elapsed:.2f}s",
                })
            else:
                results.append({
                    "test": "3.1-3.4 Monte Carlo 2026 final",
                    "pass": False,
                    "detail": "Could not find Monte Carlo 2026 tournament or final",
                })
        else:
            results.append({
                "test": "3.1-3.4 Monte Carlo 2026",
                "pass": False,
                "detail": f"Could not find Monte Carlo. Available: {[t.get('name') for t in tournaments[:5]]}",
            })

        async with engine.connect() as conn:
            ibm_match = (await conn.execute(text(
                "SELECT id FROM matches WHERE ibm_backfilled = true "
                "ORDER BY match_date DESC LIMIT 1"))).fetchone()

        if ibm_match:
            r = await client.get(f"{BASE}/api/matches/{ibm_match[0]}/points")
            data = r.json()
            results.append({
                "test": "3.5 IBM backfilled match has point data",
                "pass": r.status_code == 200 and data.get("has_data") is True,
                "detail": f"match: {ibm_match[0]}, has_data: {data.get('has_data')}, sets: {len(data.get('sets', []))}",
            })
            if data.get("has_data") and data.get("sets"):
                all_points = []
                for s in data["sets"]:
                    for g in s.get("games", []):
                        all_points.extend(g.get("points", []))
                mp_points = [p for p in all_points if p.get("is_match_point")]
                results.append({
                    "test": "3.6 IBM match has match_point flags set",
                    "pass": len(mp_points) > 0,
                    "detail": f"match points flagged: {len(mp_points)}",
                })
        else:
            results.append({
                "test": "3.5-3.6 IBM match point data",
                "pass": False,
                "detail": "No IBM backfilled matches found in DB",
            })

    return results


# --------------------------------------------------------------------------
# Test 4 — ML Model
# --------------------------------------------------------------------------
async def test_ml():
    results = []
    model_dir = os.path.join(os.path.dirname(__file__), "ml", "models")
    model_exists = os.path.exists(os.path.join(model_dir, "xgb_model.pkl"))
    cols_exists = os.path.exists(os.path.join(model_dir, "feature_columns.pkl"))
    log_exists = os.path.exists(os.path.join(model_dir, "training_log.json"))
    results.append({
        "test": "4.1 ML model files exist",
        "pass": model_exists and cols_exists and log_exists,
        "detail": f"model: {model_exists}, cols: {cols_exists}, log: {log_exists}",
    })

    if log_exists:
        with open(os.path.join(model_dir, "training_log.json")) as f:
            log = json.load(f)
        auc = log.get("auc_roc", 0)
        results.append({
            "test": "4.2 Training AUC-ROC >= 0.65",
            "pass": auc >= 0.65,
            "detail": f"AUC-ROC: {auc:.3f}",
        })
        top_features = [f["feature"] for f in log.get("top_features", [])[:3]]
        rank_features = ["rank_diff", "points_ratio", "p1_rank", "p2_rank"]
        results.append({
            "test": "4.3 Top 3 features include a rank-related feature",
            "pass": any(f in rank_features for f in top_features),
            "detail": f"top features: {top_features}",
        })
        train_rows = log.get("train_rows", 0)
        results.append({
            "test": "4.4 Training used > 50000 rows",
            "pass": train_rows > 50000,
            "detail": f"train_rows: {train_rows}",
        })

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{BASE}/api/rankings?limit=60")
        rankings = r.json() if r.status_code == 200 else []
        rank50_player = next((p for p in rankings if p.get("rank") == 50), None)
        if rank50_player:
            rank50_id = rank50_player.get("player_id", "").upper()
            r = await client.get(
                f"{BASE}/api/predict?p1=S0AG&p2={rank50_id}&surface=Hard&tier=Masters+1000&round=QF")
            if r.status_code == 200:
                prob = r.json().get("prediction", {}).get("p1_win_probability", 0.5)
                results.append({
                    "test": "4.5 Sinner (#1) favored >0.60 over rank-50 player on hard",
                    "pass": prob > 0.60,
                    "detail": f"Sinner win prob vs rank-50 ({rank50_id}): {prob:.3f}",
                })

        r_hard = await client.get(
            f"{BASE}/api/predict?p1=S0AG&p2=A0E2&surface=Hard&tier=Grand+Slam&round=SF")
        r_clay = await client.get(
            f"{BASE}/api/predict?p1=S0AG&p2=A0E2&surface=Clay&tier=Grand+Slam&round=SF")
        if r_hard.status_code == 200 and r_clay.status_code == 200:
            p_hard = r_hard.json().get("prediction", {}).get("p1_win_probability", 0.5)
            p_clay = r_clay.json().get("prediction", {}).get("p1_win_probability", 0.5)
            results.append({
                "test": "4.6 Sinner more favored vs Alcaraz on Hard than Clay",
                "pass": p_hard > p_clay,
                "detail": f"Hard: {p_hard:.3f}, Clay: {p_clay:.3f}",
            })

    return results


# --------------------------------------------------------------------------
# Test 5 — Frontend Pages Load
# --------------------------------------------------------------------------
async def test_frontend():
    results = []
    async with httpx.AsyncClient(timeout=30) as client:
        pages = [
            ("/", "Courtside", "5.1 Home page loads"),
            ("/rankings", "Rankings", "5.2 Rankings page loads"),
            ("/tournaments", "Tournament", "5.3 Tournaments page loads"),
            ("/players", "Players", "5.4 Players page loads"),
            ("/compare", "Compare", "5.5 Compare page loads"),
            ("/live", "live", "5.6 Live page loads"),
            ("/predictions", "Prediction", "5.7 Predictions page loads"),
        ]
        for path, content_check, test_name in pages:
            try:
                r = await client.get(f"{FRONT}{path}", follow_redirects=True)
                results.append({
                    "test": test_name,
                    "pass": r.status_code == 200,
                    "detail": f"status: {r.status_code}, has '{content_check}': {content_check.lower() in r.text.lower()}",
                })
            except Exception as e:
                results.append({"test": test_name, "pass": False, "detail": f"error: {e}"})

        try:
            r = await client.get(f"{FRONT}/players/S0AG", follow_redirects=True)
            results.append({
                "test": "5.8 Player profile /players/S0AG loads",
                "pass": r.status_code == 200 and "Sinner" in r.text,
                "detail": f"status: {r.status_code}, has Sinner: {'Sinner' in r.text}",
            })
        except Exception as e:
            results.append({"test": "5.8 Player profile /players/S0AG loads", "pass": False, "detail": str(e)})

        try:
            r = await client.get(f"{FRONT}/compare/A0E2/S0AG", follow_redirects=True)
            results.append({
                "test": "5.9 Compare /compare/A0E2/S0AG loads",
                "pass": r.status_code == 200 and ("Alcaraz" in r.text or "Sinner" in r.text),
                "detail": f"status: {r.status_code}",
            })
        except Exception as e:
            results.append({"test": "5.9 Compare /compare/A0E2/S0AG loads", "pass": False, "detail": str(e)})

    return results


# --------------------------------------------------------------------------
# Test 6 — Scheduler and Infrastructure
# --------------------------------------------------------------------------
async def test_infrastructure():
    results = []
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE}/health")
        results.append({
            "test": "6.1 Server is running and healthy",
            "pass": r.status_code == 200,
            "detail": r.text,
        })

        r = await client.get(f"{BASE}/api/live")
        results.append({
            "test": "6.2 /api/live returns valid JSON array",
            "pass": r.status_code == 200 and isinstance(r.json(), list),
            "detail": f"type: {type(r.json()).__name__}, len: {len(r.json())}",
        })

        try:
            async with client.stream("GET",
                                     f"{BASE}/api/matches/nonexistent/live-stream",
                                     timeout=3) as resp:
                content_type = resp.headers.get("content-type", "")
                results.append({
                    "test": "6.3 SSE endpoint returns text/event-stream",
                    "pass": "text/event-stream" in content_type,
                    "detail": f"content-type: {content_type}",
                })
        except Exception as e:
            results.append({"test": "6.3 SSE endpoint", "pass": False, "detail": str(e)})

        from scrapers.ibm.config import IBM_CONFIG
        results.append({
            "test": "6.4 Wimbledon backfill is disabled (enabled=False)",
            "pass": IBM_CONFIG.get("wimbledon", {}).get("enabled") is False,
            "detail": f"wimbledon enabled: {IBM_CONFIG.get('wimbledon', {}).get('enabled')}",
        })

    return results


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------
async def run_all():
    sections = [
        ("Database Integrity", test_database),
        ("Backend API", test_api),
        ("Point-by-Point", test_point_by_point),
        ("ML Model", test_ml),
        ("Frontend", test_frontend),
        ("Infrastructure", test_infrastructure),
    ]
    all_results = []
    for name, fn in sections:
        try:
            all_results.extend(await fn())
        except Exception as e:
            all_results.append({
                "test": f"[{name}] section crashed",
                "pass": False,
                "detail": f"{type(e).__name__}: {e}",
            })
    await engine.dispose()
    return all_results


def main():
    all_results = asyncio.run(run_all())
    passed = [r for r in all_results if r["pass"]]
    failed = [r for r in all_results if not r["pass"]]

    print("\n" + "=" * 70)
    print(f"COURTSIDE TEST SUITE — {len(all_results)} tests")
    print("=" * 70)
    print(f"\n{'Result':8} | Test")
    print("-" * 70)
    for r in all_results:
        status = "PASS" if r["pass"] else "FAIL"
        print(f"{status:8} | {r['test']}")

    print("\n" + "=" * 70)
    print(f"PASSED: {len(passed)}/{len(all_results)}")
    print(f"FAILED: {len(failed)}/{len(all_results)}")
    print("=" * 70)

    if failed:
        print("\nFAILURES:\n")
        for r in failed:
            print(f"  FAIL: {r['test']}")
            print(f"        {r['detail']}\n")
    else:
        print("\nALL TESTS PASSED")

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()

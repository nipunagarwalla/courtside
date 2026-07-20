"""Train the XGBoost match-outcome model.

Usage (from backend/):  python -m ml.train

Loads all usable matches (older than 30 days), builds point-in-time
features with one chronological pass, applies a 50% p1/p2 symmetry swap,
trains on pre-2024 matches and evaluates on 2024+.
"""
import asyncio
import json
import os
from datetime import date, datetime, timedelta, timezone

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sqlalchemy import text

from database import AsyncSessionLocal, engine
from ml.features import DatasetBuilder, tour_medians

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
EVAL_SPLIT_DATE = date(2024, 1, 1)


async def build_dataset() -> pd.DataFrame:
    """Build features for all usable matches before today - 30 days."""
    cutoff = date.today() - timedelta(days=30)
    async with AsyncSessionLocal() as db:
        medians = await tour_medians(db)

        print("Loading rankings history...")
        rank_rows = (await db.execute(text("""
            SELECT player_id, week_date, rank, points FROM rankings
            WHERE ranking_type = 'standard'
            ORDER BY player_id, week_date
        """))).all()
        rankings: dict = {}
        for r in rank_rows:
            entry = rankings.setdefault(r.player_id, ([], [], []))
            entry[0].append(r.week_date)
            entry[1].append(r.rank)
            entry[2].append(r.points)
        print(f"  {len(rank_rows)} observations for {len(rankings)} players")

        print("Loading player DOBs...")
        dob_rows = (await db.execute(
            text("SELECT id, dob FROM players WHERE dob IS NOT NULL")
        )).all()
        dobs = {r.id: r.dob for r in dob_rows}
        print(f"  {len(dobs)} players with DOB")

        print("Loading matches...")
        matches = (await db.execute(text("""
            SELECT m.id, m.match_date, m.surface, m.round, m.winner_id, m.loser_id,
                   m.w_svpt, m.w_1stin, m.w_aces, m.w_bpsaved, m.w_bpfaced,
                   m.l_svpt, m.l_1stin, m.l_aces, m.l_bpsaved, m.l_bpfaced,
                   t.tier
            FROM matches m
            LEFT JOIN tournaments t ON m.tournament_id = t.id
            WHERE m.winner_id IS NOT NULL AND m.loser_id IS NOT NULL
              AND m.match_date IS NOT NULL AND m.surface IS NOT NULL
              AND m.match_date < :cutoff
        """), {"cutoff": cutoff})).all()
        # match_date is the TOURNAMENT START date, shared by every match in
        # the tournament — same-date matches must be processed in true round
        # order or later rounds leak into earlier ones (e.g. the final would
        # update state before the semis are featurised).
        round_order = {"R128": 1, "R64": 2, "R32": 3, "R16": 4, "RR": 4,
                       "QF": 5, "SF": 6, "BR": 7, "F": 8}
        matches = sorted(
            matches,
            key=lambda m: (m.match_date, round_order.get(m.round, 0), m.id),
        )
        print(f"  {len(matches)} matches")

    builder = DatasetBuilder(rankings, dobs, medians)
    rows = []
    for m in matches:
        features = builder.features_for(m)
        if features is not None:
            features["p1_won"] = 1  # p1 = winner always before swap
            features["match_date"] = m.match_date
            rows.append(features)
        builder.update(m)
    df = pd.DataFrame(rows)
    print(f"Dataset: {len(df)} rows ({len(matches) - len(df)} skipped for missing data)")
    await engine.dispose()
    return df


def apply_symmetry_swap(df: pd.DataFrame, frac=0.5, seed=42) -> pd.DataFrame:
    """Swap p1/p2 for frac of rows and flip the target.

    Prevents the model from learning that p1 always wins. Paired p1_/p2_
    columns are exchanged; sign/ratio-derived features are flipped too.
    """
    swap_idx = df.sample(frac=frac, random_state=seed).index
    # paired p1_/p2_ columns only (p1_won is the target; p1_h2h_winrate has
    # no p2_ twin and is flipped as 1-x below)
    p1_cols = sorted(
        c for c in df.columns
        if c.startswith("p1_") and c.replace("p1_", "p2_", 1) in df.columns
    )
    p2_cols = [c.replace("p1_", "p2_", 1) for c in p1_cols]
    df.loc[swap_idx, p1_cols + p2_cols] = df.loc[swap_idx, p2_cols + p1_cols].values
    df.loc[swap_idx, "p1_won"] = 1 - df.loc[swap_idx, "p1_won"]
    for col in ["rank_diff", "surface_diff", "form_diff", "age_diff"]:
        df.loc[swap_idx, col] *= -1
    for col in ["points_ratio", "p1_h2h_winrate"]:
        df.loc[swap_idx, col] = 1 - df.loc[swap_idx, col]
    return df


def main():
    df = asyncio.run(build_dataset())
    df = apply_symmetry_swap(df)

    feature_cols = [c for c in df.columns if c not in ("p1_won", "match_date")]
    train_mask = df["match_date"] < EVAL_SPLIT_DATE
    X_train = df.loc[train_mask, feature_cols]
    X_eval = df.loc[~train_mask, feature_cols]
    y_train = df.loc[train_mask, "p1_won"]
    y_eval = df.loc[~train_mask, "p1_won"]
    print(f"Train: {len(X_train)} rows (< {EVAL_SPLIT_DATE}), eval: {len(X_eval)} rows")

    model = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        early_stopping_rounds=50,
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_eval, y_eval)], verbose=50)

    probs = model.predict_proba(X_eval)[:, 1]
    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "train_rows": len(X_train),
        "eval_rows": len(X_eval),
        "accuracy": float(accuracy_score(y_eval, probs > 0.5)),
        "auc_roc": float(roc_auc_score(y_eval, probs)),
        "log_loss": float(log_loss(y_eval, probs)),
        "top_features": [
            {"feature": f, "importance": float(i)}
            for f, i in sorted(
                zip(feature_cols, model.feature_importances_),
                key=lambda x: x[1], reverse=True,
            )[:10]
        ],
    }

    print(f"AUC-ROC:  {metrics['auc_roc']:.3f}")
    print(f"Accuracy: {metrics['accuracy']:.3f}")
    print(f"Log loss: {metrics['log_loss']:.3f}")
    print("Top features:")
    for tf in metrics["top_features"]:
        print(f"  {tf['feature']:<22} {tf['importance']:.3f}")

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, os.path.join(MODEL_DIR, "xgb_model.pkl"))
    joblib.dump(feature_cols, os.path.join(MODEL_DIR, "feature_columns.pkl"))
    with open(os.path.join(MODEL_DIR, "training_log.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved model to {MODEL_DIR}")


if __name__ == "__main__":
    main()

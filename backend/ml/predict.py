import os

import joblib
import numpy as np

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


class MatchPredictor:
    def __init__(self):
        model_path = os.path.join(MODEL_DIR, "xgb_model.pkl")
        cols_path = os.path.join(MODEL_DIR, "feature_columns.pkl")
        if not os.path.exists(model_path):
            raise FileNotFoundError("Model not trained yet")
        self.model = joblib.load(model_path)
        self.cols = joblib.load(cols_path)
        self.imp = dict(zip(self.cols, self.model.feature_importances_))

    def predict(self, features: dict) -> dict:
        X = np.array([[features.get(c, 0) for c in self.cols]], dtype=float)
        prob = float(self.model.predict_proba(X)[0][1])
        return {
            "p1_win_probability": round(prob, 3),
            "p2_win_probability": round(1 - prob, 3),
            "confidence": self._confidence(prob),
            "key_factors": self._factors(features),
        }

    def _confidence(self, p: float) -> str:
        if p > 0.72 or p < 0.28:
            return "High"
        if p > 0.62 or p < 0.38:
            return "Moderate"
        return "Toss-up"

    def _factors(self, f: dict) -> list[dict]:
        candidates = [
            ("rank_diff",      "Ranking advantage"),
            ("h2h_total",      "Head-to-head record"),
            ("surface_diff",   "Surface preference"),
            ("form_diff",      "Recent form"),
            ("p1_bp_save_pct", "Break point defence"),
            ("p1_days_rest",   "Rest advantage"),
        ]
        out = [
            {"factor": label, "importance": round(float(self.imp.get(col, 0)), 4)}
            for col, label in candidates
            if abs(f.get(col, 0)) > 0.05
        ]
        return sorted(out, key=lambda x: x["importance"], reverse=True)[:3]

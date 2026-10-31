"""Load the trained invoice-count model and serve predictions."""
from __future__ import annotations

from datetime import date
from functools import lru_cache

import joblib
import pandas as pd

from app.ml.train_model import MODEL_PATH, SHIFTS, feature_frame, train_baseline


@lru_cache(maxsize=4)
def _load_saved_model(model_path: str, mtime_ns: int = 0):
    saved = joblib.load(model_path)
    return saved["model"]


@lru_cache(maxsize=1)
def _fallback_model(raw_mtime_ns: int):
    return train_baseline()[0]


def predict_count(target_date: str, shift: str, is_holiday: bool) -> int:
    """Return an integer count, compatible with existing POST /api/predict."""
    if not isinstance(target_date, str):
        raise ValueError("target_date must be YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(target_date)
    except (ValueError, TypeError) as exc:
        raise ValueError("target_date must be YYYY-MM-DD") from exc
    if parsed.isoformat() != target_date:
        raise ValueError("target_date must be YYYY-MM-DD")
    if shift not in SHIFTS:
        raise ValueError(f"shift must be one of: {', '.join(SHIFTS)}")
    if not isinstance(is_holiday, bool):
        raise ValueError("is_holiday must be boolean")
    row = pd.DataFrame([{"date": target_date, "shift": shift, "is_holiday": is_holiday}])
    if MODEL_PATH.exists():
        model = _load_saved_model(str(MODEL_PATH), MODEL_PATH.stat().st_mtime_ns)
    else:
        from app.services.data_service import RAW_PATH

        model = _fallback_model(RAW_PATH.stat().st_mtime_ns)
    prediction = float(model.predict(feature_frame(row))[0])
    return max(0, int(round(prediction)))

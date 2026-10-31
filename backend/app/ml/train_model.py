"""Invoice-count model training and date-based evaluation."""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

SHIFTS = ("Night", "Morning", "Afternoon", "Evening")
SHIFT_TO_CODE = {name: index for index, name in enumerate(SHIFTS)}
FEATURES = ["day_of_week", "month", "shift_code", "is_holiday"]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = PROJECT_ROOT / "models" / "invoice_count_rf.joblib"


def feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Transform rows with date/shift/holiday to the agreed model features."""
    out = df.copy()
    if "date" in out.columns:
        dates = pd.to_datetime(out["date"], format="%Y-%m-%d", errors="raise")
        out["day_of_week"] = dates.dt.dayofweek
        out["month"] = dates.dt.month
    if "shift" not in out.columns or not out["shift"].isin(SHIFTS).all():
        raise ValueError(f"shift must be one of: {', '.join(SHIFTS)}")
    if "is_holiday" not in out.columns or out["is_holiday"].isna().any():
        raise ValueError("is_holiday must contain non-null booleans")
    if not out["is_holiday"].map(lambda v: isinstance(v, (bool, np.bool_))).all():
        raise ValueError("is_holiday must be boolean")
    out["shift_code"] = out["shift"].map(SHIFT_TO_CODE)
    return out[FEATURES].astype(float)


def build_training_data() -> pd.DataFrame:
    """Use the team's data service, importing lazily so fixtures work independently."""
    from app.services.data_service import aggregate_invoice_counts, load_enriched_data

    grouped = aggregate_invoice_counts(load_enriched_data())
    return prepare_aggregates(grouped)


def prepare_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Validate grouped invoice-count schema and normalize date order."""
    required = {"date", "shift", "is_holiday", "invoice_count"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing grouped columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("No invoice-count records to train on")
    out = df[list(required)].copy()
    out["date"] = pd.to_datetime(out["date"], errors="raise").dt.strftime("%Y-%m-%d")
    out["invoice_count"] = pd.to_numeric(out["invoice_count"], errors="raise")
    if not np.isfinite(out["invoice_count"]).all() or (out["invoice_count"] < 0).any():
        raise ValueError("invoice_count must be finite and non-negative")
    if out["date"].isna().any():
        raise ValueError("date must be non-null")
    if out.duplicated(["date", "shift", "is_holiday"]).any():
        raise ValueError("Duplicate date + shift + is_holiday groups")
    feature_frame(out)
    return out.sort_values(["date", "shift", "is_holiday"]).reset_index(drop=True)


def make_model() -> RandomForestRegressor:
    return RandomForestRegressor(n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=-1)


def train_baseline():
    """Keep original repo's function signature for other modules."""
    from app.ml.evaluate_model import tune_model

    grouped = build_training_data()
    model, _ = tune_model(grouped)
    return model, grouped


def train_and_save(df: pd.DataFrame | None = None, path: Path = MODEL_PATH) -> Path:
    """Tune and refit the selected model on the full history."""
    from app.ml.evaluate_model import tune_model

    grouped = prepare_aggregates(df) if df is not None else build_training_data()
    model, tuning = tune_model(grouped)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "n_rows": len(grouped),
                 "tuning": tuning, "schema_version": 2}, path, compress=3)
    from app.ml.predict_model import _load_saved_model

    _load_saved_model.cache_clear()
    return path

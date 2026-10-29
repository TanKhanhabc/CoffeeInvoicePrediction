"""Invoice-count forecasting owned by Phạm Tấn Khánh.

Interface used by the team's API: predict_count(date, shift, is_holiday) -> int.
Evaluation uses held-out *dates* (never random rows) to avoid time leakage.
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

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


def chronological_split(df: pd.DataFrame, test_fraction: float = 0.2):
    """Reserve last 20% of *distinct dates*, not randomly selected shifts."""
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1")
    dates = sorted(df["date"].unique())
    if len(dates) < 5:
        raise ValueError("At least 5 distinct dates are needed for evaluation")
    n_test = max(1, int(np.ceil(len(dates) * test_fraction)))
    cutoff = dates[-n_test]
    train = df[df["date"] < cutoff].copy()
    test = df[df["date"] >= cutoff].copy()
    if train.empty:
        raise ValueError("test_fraction leaves no training dates")
    return train, test


class ShiftMeanBaseline:
    """Mean transaction volume for each shift, falling back to overall mean."""

    def fit(self, df: pd.DataFrame):
        self.shift_means = df.groupby("shift")["invoice_count"].mean().to_dict()
        self.overall_mean = float(df["invoice_count"].mean())
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return df["shift"].map(self.shift_means).fillna(self.overall_mean).to_numpy(dtype=float)


def make_model() -> RandomForestRegressor:
    return RandomForestRegressor(n_estimators=200, min_samples_leaf=2, random_state=42, n_jobs=-1)


class SelectedForecaster:
    """Keep the DataFrame prediction interface for both baseline and forest."""

    def __init__(self, estimator, name):
        self.estimator = estimator
        self.name = name

    def predict(self, features):
        if self.name == "baseline_shift_mean":
            shifts = features["shift_code"].map(dict(enumerate(SHIFTS)))
            return self.estimator.predict(pd.DataFrame({"shift": shifts}))
        return self.estimator.predict(features)


def tune_model(df: pd.DataFrame):
    """Select using expanding date windows; never inspect the outer test set."""
    dates = np.array(sorted(df["date"].unique()))
    if len(dates) < 3:
        raise ValueError("At least 3 distinct dates are needed for tuning")
    candidates = {"baseline_shift_mean": None}
    for leaf in (2, 8, 20):
        for depth in (6, None):
            candidates[f"rf_leaf{leaf}_depth{depth}"] = {
                "min_samples_leaf": leaf, "max_depth": depth,
            }
    scores = {name: [] for name in candidates}
    folds = []
    for train_idx, valid_idx in TimeSeriesSplit(n_splits=min(3, len(dates) - 1)).split(dates):
        train = df[df["date"].isin(dates[train_idx])]
        valid = df[df["date"].isin(dates[valid_idx])]
        x_train, x_valid = feature_frame(train), feature_frame(valid)
        folds.append({"train_end": train["date"].max(), "validation_start": valid["date"].min(),
                      "validation_end": valid["date"].max()})
        for name, params in candidates.items():
            if params is None:
                prediction = ShiftMeanBaseline().fit(train).predict(valid)
            else:
                estimator = make_model().set_params(**params)
                estimator.fit(x_train, train["invoice_count"])
                prediction = estimator.predict(x_valid)
            scores[name].append(float(mean_absolute_error(valid["invoice_count"], prediction)))
    averages = {name: float(np.mean(values)) for name, values in scores.items()}
    selected = min(averages, key=averages.get)
    params = candidates[selected]
    estimator = (ShiftMeanBaseline().fit(df) if params is None else
                 make_model().set_params(**params).fit(feature_frame(df), df["invoice_count"]))
    return SelectedForecaster(estimator, selected), {
        "selected_model": selected, "selection_metric": "MAE",
        "cv_mae": averages, "folds": folds, "selected_params": params,
    }


def metric_pair(y_true, y_pred) -> dict:
    return {
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
    }


def evaluate_models(df: pd.DataFrame, test_fraction: float = 0.2) -> dict:
    """Measure baseline and Random Forest on identical unseen future dates."""
    df = prepare_aggregates(df)
    train, test = chronological_split(df, test_fraction)
    baseline = ShiftMeanBaseline().fit(train)
    rf = make_model()
    rf.fit(feature_frame(train), train["invoice_count"])
    baseline_metrics = metric_pair(test["invoice_count"], baseline.predict(test))
    forest_metrics = metric_pair(test["invoice_count"], rf.predict(feature_frame(test)))
    tuned, tuning = tune_model(train)
    tuned_predictions = tuned.predict(feature_frame(test))
    return {
        "split": "chronological_by_distinct_date",
        "train_start": train["date"].min(),
        "train_end": train["date"].max(),
        "test_start": test["date"].min(),
        "test_end": test["date"].max(),
        "train_rows": len(train),
        "test_rows": len(test),
        "baseline_shift_mean": baseline_metrics,
        "random_forest": forest_metrics,
        "tuning": tuning,
        "optimized": metric_pair(test["invoice_count"], tuned_predictions),
        "optimized_by_shift": {
            shift: metric_pair(test.loc[test["shift"] == shift, "invoice_count"],
                               tuned_predictions[(test["shift"] == shift).to_numpy()])
            for shift in SHIFTS if (test["shift"] == shift).any()
        },
        "rf_beats_baseline_mae": forest_metrics["MAE"] < baseline_metrics["MAE"],
        "rf_beats_baseline_rmse": forest_metrics["RMSE"] < baseline_metrics["RMSE"],
    }


def train_baseline():
    """Keep original repo's function signature for other modules."""
    grouped = build_training_data()
    model, _ = tune_model(grouped)
    return model, grouped


def train_and_save(df: pd.DataFrame | None = None, path: Path = MODEL_PATH) -> Path:
    """Tune and refit on full history; evaluate_models provides holdout scores."""
    grouped = prepare_aggregates(df) if df is not None else build_training_data()
    model, tuning = tune_model(grouped)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "n_rows": len(grouped),
                 "tuning": tuning, "schema_version": 2}, path, compress=3)
    _load_saved_model.cache_clear()
    return path


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

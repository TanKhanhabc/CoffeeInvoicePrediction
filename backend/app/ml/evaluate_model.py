"""Chronological model evaluation and time-series model selection."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

from app.ml.train_model import (
    SHIFTS,
    feature_frame,
    make_model,
    prepare_aggregates,
)

RESULTS_PATH = Path(__file__).resolve().parents[3] / "results" / "evaluation_metrics.json"


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


def save_evaluation_results(
    results: dict,
    path: Path = RESULTS_PATH,
) -> Path:
    """Write evaluation metrics as formatted UTF-8 JSON and return the file path."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return destination

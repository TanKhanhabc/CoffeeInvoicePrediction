import numpy as np
import pandas as pd
import pytest

from app.ml import predict_model, train_model as ml


def sample_data():
    return pd.DataFrame([
        {"date": day.strftime("%Y-%m-%d"), "shift": shift,
         "is_holiday": False, "invoice_count": index * 10}
        for day in pd.date_range("2023-01-01", periods=30)
        for index, shift in enumerate(ml.SHIFTS)
    ])


def test_tuning_keeps_holdout_dates_out(monkeypatch):
    monkeypatch.setattr(ml, "make_model", lambda: ml.RandomForestRegressor(
        n_estimators=5, n_jobs=1, random_state=42))
    report = ml.evaluate_models(sample_data())
    assert all(fold["train_end"] < fold["validation_start"] <=
               fold["validation_end"] < report["test_start"]
               for fold in report["tuning"]["folds"])
    assert report["tuning"]["selected_model"] == "baseline_shift_mean"
    assert report["optimized"]["MAE"] == 0


def test_saved_model_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(ml, "make_model", lambda: ml.RandomForestRegressor(
        n_estimators=5, n_jobs=1, random_state=42))
    path = ml.train_and_save(sample_data(), tmp_path / "model.joblib")
    model = predict_model._load_saved_model(str(path))
    assert model.predict(ml.feature_frame(sample_data())).tolist() == sample_data()["invoice_count"].tolist()


@pytest.mark.parametrize("invalid", [np.inf, -1, np.nan])
def test_reject_invalid_counts(invalid):
    df = sample_data().astype({"invoice_count": float})
    df.loc[0, "invoice_count"] = invalid
    with pytest.raises(ValueError, match="finite and non-negative"):
        ml.prepare_aggregates(df)


def test_split_requires_training_dates():
    with pytest.raises(ValueError, match="no training dates"):
        ml.chronological_split(sample_data(), 0.999)

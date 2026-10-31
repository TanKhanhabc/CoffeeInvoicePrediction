"""Backward-compatible imports for the split training and prediction modules."""
from app.ml.predict_model import _fallback_model, _load_saved_model, predict_count
from app.ml.evaluate_model import (
    SelectedForecaster,
    ShiftMeanBaseline,
    chronological_split,
    evaluate_models,
    metric_pair,
    save_evaluation_results,
    tune_model,
)
from app.ml.train_model import (
    FEATURES,
    MODEL_PATH,
    SHIFTS,
    SHIFT_TO_CODE,
    build_training_data,
    feature_frame,
    make_model,
    prepare_aggregates,
    train_and_save,
    train_baseline,
)

__all__ = [
    "FEATURES",
    "MODEL_PATH",
    "SHIFTS",
    "SHIFT_TO_CODE",
    "SelectedForecaster",
    "ShiftMeanBaseline",
    "build_training_data",
    "chronological_split",
    "evaluate_models",
    "feature_frame",
    "make_model",
    "metric_pair",
    "predict_count",
    "prepare_aggregates",
    "save_evaluation_results",
    "train_and_save",
    "train_baseline",
    "tune_model",
]

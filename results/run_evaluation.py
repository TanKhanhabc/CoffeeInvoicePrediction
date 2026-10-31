"""Run from repository root: python results/run_evaluation.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.evaluate_model import evaluate_models, save_evaluation_results
from app.ml.train_model import build_training_data, train_and_save


def main():
    grouped = build_training_data()
    metrics = evaluate_models(grouped)
    destination = save_evaluation_results(metrics)
    model_path = train_and_save(grouped)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(f"Saved metrics: {destination}")
    print(f"Saved model:   {model_path}")


if __name__ == "__main__":
    main()

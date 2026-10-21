"""Run from repository root: python results/run_evaluation.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.model_service import build_training_data, evaluate_models, train_and_save


def main():
    grouped = build_training_data()
    metrics = evaluate_models(grouped)
    destination = ROOT / "results" / "evaluation_metrics.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    model_path = train_and_save(grouped)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(f"Saved metrics: {destination}")
    print(f"Saved model:   {model_path}")


if __name__ == "__main__":
    main()

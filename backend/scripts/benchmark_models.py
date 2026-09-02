#!/usr/bin/env python3
"""Benchmark Seasonal, Random Forest, LightGBM and an available TFT checkpoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.ml.forecasting import forecast_with_evaluation  # noqa: E402
from app.services.preprocessing import prepare_readings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmark.json"))
    parser.add_argument("--include-tft", action="store_true")
    args = parser.parse_args()
    raw = pd.read_csv(args.csv, usecols=["timestamp", "power_kw"])
    frame, quality = prepare_readings(raw.to_dict("records"))
    models = ["Seasonal baseline", "Random Forest", "LightGBM"]
    if args.include_tft:
        models.append("TFT")
    result = forecast_with_evaluation(frame, models)
    report = {
        "dataset": str(args.csv),
        "reading_count": len(frame),
        "quality": quality,
        "selected_model": result["model"],
        "evaluation": result["evaluation"],
        "model_capabilities": result["model_capabilities"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

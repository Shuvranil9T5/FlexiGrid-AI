"""Feature engineering shared by Random Forest and LightGBM forecasts."""

from __future__ import annotations

import math

import pandas as pd


FEATURE_COLUMNS = [
    "slot",
    "day_of_week",
    "is_weekend",
    "slot_sin",
    "slot_cos",
    "dow_sin",
    "dow_cos",
    "lag_1",
    "lag_4",
    "lag_96",
    "rolling_mean_4",
    "rolling_mean_96",
]


def build_supervised_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Build leakage-safe features using only values available before each target."""
    work = frame.copy()
    work["is_weekend"] = (work.index.dayofweek >= 5).astype(int)
    work["slot_sin"] = work["slot"].map(lambda value: math.sin(2 * math.pi * value / 96))
    work["slot_cos"] = work["slot"].map(lambda value: math.cos(2 * math.pi * value / 96))
    work["dow_sin"] = work["day_of_week"].map(lambda value: math.sin(2 * math.pi * value / 7))
    work["dow_cos"] = work["day_of_week"].map(lambda value: math.cos(2 * math.pi * value / 7))
    work["lag_1"] = work["power_kw"].shift(1)
    work["lag_4"] = work["power_kw"].shift(4)
    work["lag_96"] = work["power_kw"].shift(96)
    shifted = work["power_kw"].shift(1)
    work["rolling_mean_4"] = shifted.rolling(4).mean()
    work["rolling_mean_96"] = shifted.rolling(96).mean()
    return work.dropna(subset=FEATURE_COLUMNS + ["power_kw"])


def next_feature_row(timestamp: pd.Timestamp, history: list[float]) -> dict[str, float]:
    if len(history) < 96:
        raise ValueError("At least 96 history points are required for recursive forecasting")
    slot = timestamp.hour * 4 + timestamp.minute // 15
    day_of_week = timestamp.dayofweek
    return {
        "slot": slot,
        "day_of_week": day_of_week,
        "is_weekend": int(day_of_week >= 5),
        "slot_sin": math.sin(2 * math.pi * slot / 96),
        "slot_cos": math.cos(2 * math.pi * slot / 96),
        "dow_sin": math.sin(2 * math.pi * day_of_week / 7),
        "dow_cos": math.cos(2 * math.pi * day_of_week / 7),
        "lag_1": history[-1],
        "lag_4": history[-4],
        "lag_96": history[-96],
        "rolling_mean_4": sum(history[-4:]) / 4,
        "rolling_mean_96": sum(history[-96:]) / 96,
    }

"""Optional genuine Temporal Fusion Transformer integration.

TFT training is deliberately offline because training a Transformer inside a web
request would make the API unreliable. Install ``requirements-tft.txt`` and run
``scripts/train_tft.py``. The API automatically discovers the checkpoint.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import pandas as pd


def checkpoint_path() -> Path:
    configured = os.getenv("FLEXIGRID_TFT_CHECKPOINT")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "artifacts" / "tft" / "best.ckpt"


def dependency_status() -> tuple[bool, str]:
    try:
        import torch  # noqa: F401
        import pytorch_forecasting  # noqa: F401
    except ImportError:
        return False, "Install backend/requirements-tft.txt"
    if not checkpoint_path().exists():
        return False, "Train a checkpoint with backend/scripts/train_tft.py"
    return True, "checkpoint ready"


def to_tft_frame(frame: pd.DataFrame, series_id: str = "building_001") -> pd.DataFrame:
    data = frame.reset_index()[["timestamp", "power_kw"]].copy()
    data["series_id"] = series_id
    data["time_idx"] = np.arange(len(data), dtype=int)
    slot = data["timestamp"].dt.hour * 4 + data["timestamp"].dt.minute // 15
    dow = data["timestamp"].dt.dayofweek
    data["slot_sin"] = np.sin(2 * math.pi * slot / 96)
    data["slot_cos"] = np.cos(2 * math.pi * slot / 96)
    data["dow_sin"] = np.sin(2 * math.pi * dow / 7)
    data["dow_cos"] = np.cos(2 * math.pi * dow / 7)
    data["is_weekend"] = (dow >= 5).astype(float)
    return data


def forecast_from_checkpoint(frame: pd.DataFrame) -> list[float]:
    ready, reason = dependency_status()
    if not ready:
        raise RuntimeError(reason)

    import torch
    from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet

    model = TemporalFusionTransformer.load_from_checkpoint(str(checkpoint_path()))
    history = to_tft_frame(frame)
    last_time = history["timestamp"].iloc[-1]
    future_times = pd.date_range(last_time + pd.Timedelta(minutes=15), periods=96, freq="15min")
    future_source = pd.DataFrame({"timestamp": future_times, "power_kw": 0.0}).set_index("timestamp")
    future_frame = to_tft_frame(future_source, series_id=str(history["series_id"].iloc[-1]))
    future_frame["time_idx"] = np.arange(len(history), len(history) + 96, dtype=int)
    prediction_data = pd.concat([history, future_frame], ignore_index=True)
    dataset = TimeSeriesDataSet.from_parameters(
        model.dataset_parameters,
        prediction_data,
        predict=True,
        stop_randomization=True,
    )
    loader = dataset.to_dataloader(train=False, batch_size=1, num_workers=0)
    with torch.inference_mode():
        prediction = model.predict(loader, mode="prediction")
    values = np.asarray(prediction).reshape(-1)[-96:]
    return [round(max(0.0, float(value)), 3) for value in values]

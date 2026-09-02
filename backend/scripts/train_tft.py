#!/usr/bin/env python3
"""Train a genuine PyTorch Forecasting Temporal Fusion Transformer checkpoint."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.ml.tft import to_tft_frame  # noqa: E402
from app.services.preprocessing import prepare_readings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("artifacts/tft/best.ckpt"))
    args = parser.parse_args()

    try:
        import lightning.pytorch as pl
        from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
        from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
        from pytorch_forecasting.data import GroupNormalizer
        from pytorch_forecasting.metrics import QuantileLoss
    except ImportError as exc:
        raise SystemExit("Install dependencies with: pip install -r requirements-tft.txt") from exc

    pl.seed_everything(42, workers=True)

    raw = pd.read_csv(args.csv, usecols=["timestamp", "power_kw"])
    prepared, _ = prepare_readings(raw.to_dict("records"))
    if len(prepared) < 14 * 96:
        raise SystemExit("TFT training requires at least 14 complete days")
    # A stable group id lets the resulting single-series checkpoint serve any
    # uploaded building history after the same 15-minute preprocessing.
    data = to_tft_frame(prepared, series_id="building_001")
    training_cutoff = int(data["time_idx"].max() - 96)
    training = TimeSeriesDataSet(
        data[data.time_idx <= training_cutoff],
        time_idx="time_idx",
        target="power_kw",
        group_ids=["series_id"],
        max_encoder_length=7 * 96,
        max_prediction_length=96,
        time_varying_known_reals=[
            "time_idx", "slot_sin", "slot_cos", "dow_sin", "dow_cos", "is_weekend"
        ],
        time_varying_unknown_reals=["power_kw"],
        target_normalizer=GroupNormalizer(groups=["series_id"], transformation="softplus"),
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
    )
    validation = TimeSeriesDataSet.from_dataset(training, data, predict=True, stop_randomization=True)
    train_loader = training.to_dataloader(train=True, batch_size=64, num_workers=0)
    validation_loader = validation.to_dataloader(train=False, batch_size=64, num_workers=0)
    checkpoint = ModelCheckpoint(monitor="val_loss", mode="min", save_top_k=1)
    trainer = pl.Trainer(
        max_epochs=args.epochs,
        accelerator="auto",
        devices=1,
        gradient_clip_val=0.1,
        callbacks=[checkpoint, EarlyStopping(monitor="val_loss", patience=3, mode="min")],
        logger=False,
        enable_model_summary=True,
    )
    model = TemporalFusionTransformer.from_dataset(
        training,
        learning_rate=0.02,
        hidden_size=32,
        attention_head_size=4,
        dropout=0.15,
        hidden_continuous_size=16,
        output_size=7,
        loss=QuantileLoss(),
        reduce_on_plateau_patience=2,
    )
    trainer.fit(model, train_loader, validation_loader)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(checkpoint.best_model_path, args.output)
    print(f"Saved TFT checkpoint to {args.output}")


if __name__ == "__main__":
    main()

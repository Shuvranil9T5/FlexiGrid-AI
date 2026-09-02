"""Catalog and sample access for the two real public energy datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"

DATASETS = {
    "uci": {
        "id": "uci",
        "name": "UCI ElectricityLoadDiagrams20112014",
        "source": "UCI Machine Learning Repository",
        "native_resolution": "15 minutes",
        "sample_file": "uci_mt001_30days_15min.csv",
        "sample_series": "MT_001",
        "license": "CC BY 4.0",
        "source_url": "https://archive.ics.uci.edu/dataset/321/electricityloaddiagrams20112014",
    },
    "iblend": {
        "id": "iblend",
        "name": "I-BLEND / IIIT-Delhi campus energy dataset",
        "source": "IIIT-Delhi / Springer Nature Figshare",
        "native_resolution": "1 minute (aggregated to 15 minutes)",
        "sample_file": "iblend_academic_30days_15min.csv",
        "sample_series": "Academic building",
        "license": "Check the original dataset record before redistribution",
        "source_url": "https://springernature.figshare.com/articles/dataset/Energy_dataset_of_IIITD/6007637",
    },
}


def dataset_catalog() -> list[dict]:
    output = []
    for item in DATASETS.values():
        sample_path = SAMPLE_DIR / item["sample_file"]
        output.append({**item, "sample_available": sample_path.exists()})
    return output


def load_sample(dataset_id: str) -> tuple[list[dict], dict]:
    metadata = DATASETS.get(dataset_id.lower())
    if metadata is None:
        raise ValueError("Dataset must be 'uci' or 'iblend'")
    path = SAMPLE_DIR / metadata["sample_file"]
    if not path.exists():
        raise ValueError(
            f"Prepared sample is missing. Run backend/scripts/prepare_real_datasets.py for {dataset_id}."
        )
    frame = pd.read_csv(path, usecols=["timestamp", "power_kw"])
    return frame.to_dict("records"), metadata

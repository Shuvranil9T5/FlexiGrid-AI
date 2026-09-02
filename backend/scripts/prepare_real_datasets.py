#!/usr/bin/env python3
"""Create compact, project-ready 15-minute samples from the raw archives.

The script does not download data and never modifies the raw ZIP files. Pass the
archives previously downloaded from UCI and I-BLEND/Figshare (or its mirror).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


def prepare_uci(raw_zip: Path, destination: Path, client: str, days: int) -> int:
    try:
        client_position = int(client.split("_")[-1])
    except (ValueError, IndexError) as exc:
        raise ValueError("UCI client must use the MT_001 ... MT_370 naming format") from exc
    with ZipFile(raw_zip) as archive, archive.open("LD2011_2014.txt") as source:
        frame = pd.read_csv(
            source,
            sep=";",
            decimal=",",
            usecols=[0, client_position],
            low_memory=False,
        )
    frame.columns = ["timestamp", "power_kw"]
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["power_kw"] = pd.to_numeric(frame["power_kw"], errors="coerce")
    frame = frame.dropna().sort_values("timestamp")
    nonzero = frame.index[frame["power_kw"] > 0]
    if nonzero.empty:
        raise ValueError(f"{client} contains no non-zero readings")
    frame = frame.loc[nonzero[0]:].tail(days * 96).copy()
    frame["dataset"] = "UCI"
    frame["series_id"] = client
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, float_format="%.6f")
    return len(frame)


def prepare_iblend(raw_zip: Path, destination: Path, building: str, days: int) -> int:
    source_file = "all_buildings_power.csv"
    with ZipFile(raw_zip) as archive, archive.open(source_file) as source:
        frame = pd.read_csv(
            source,
            usecols=["timestamp", building],
            nrows=days * 24 * 60,
            na_values=["NA"],
        )
    frame.columns = ["timestamp", "power_w"]
    timestamp = pd.to_datetime(frame["timestamp"], unit="s", utc=True)
    frame["timestamp"] = timestamp.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    frame["power_kw"] = pd.to_numeric(frame["power_w"], errors="coerce") / 1000.0
    frame = frame.dropna(subset=["timestamp", "power_kw"])
    frame = frame.set_index("timestamp")[["power_kw"]].resample("15min").mean().interpolate(limit=8)
    frame = frame.dropna().reset_index()
    frame["dataset"] = "I-BLEND"
    frame["series_id"] = building
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False, float_format="%.6f")
    return len(frame)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uci-zip", type=Path, required=True)
    parser.add_argument("--iblend-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/samples"))
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--uci-client", default="MT_001")
    parser.add_argument("--iblend-building", default="Academic")
    args = parser.parse_args()
    if args.days < 7:
        parser.error("--days must be at least 7")

    uci_rows = prepare_uci(
        args.uci_zip,
        args.output_dir / f"uci_{args.uci_client.lower().replace('_', '')}_{args.days}days_15min.csv",
        args.uci_client,
        args.days,
    )
    iblend_rows = prepare_iblend(
        args.iblend_zip,
        args.output_dir / f"iblend_{args.iblend_building.lower().replace(' ', '_')}_{args.days}days_15min.csv",
        args.iblend_building,
        args.days,
    )
    print(f"Prepared UCI rows: {uci_rows}")
    print(f"Prepared I-BLEND rows: {iblend_rows}")


if __name__ == "__main__":
    main()

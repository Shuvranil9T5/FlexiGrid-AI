import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN


def _duration_for_start(start: dict, events: list[dict]) -> int | None:
    start_time = pd.Timestamp(start["timestamp"])
    for stop in events:
        if stop["event_type"] != "STOP":
            continue
        minutes = (pd.Timestamp(stop["timestamp"]) - start_time).total_seconds() / 60
        magnitude_ratio = abs(abs(stop["change_kw"]) - start["change_kw"]) / max(start["change_kw"], 0.1)
        if 15 <= minutes <= 480 and magnitude_ratio <= 0.45:
            return int(round(minutes / 15))
    return None


def detect_events(frame: pd.DataFrame, threshold_kw: float = 0.8) -> list[dict]:
    candidates = frame[frame["load_change"].abs() >= threshold_kw]
    events = []
    for timestamp, row in candidates.iterrows():
        events.append({
            "timestamp": timestamp.isoformat(),
            "slot": int(row["slot"]),
            "change_kw": round(float(row["load_change"]), 3),
            "event_type": "START" if row["load_change"] > 0 else "STOP",
            "confidence": round(min(0.99, 0.55 + abs(float(row["load_change"])) / 10), 2),
        })
    return events


def discover_patterns(events: list[dict]) -> list[dict]:
    starts = [event for event in events if event["event_type"] == "START"]
    if len(starts) < 2:
        return []
    powers = np.asarray([event["change_kw"] for event in starts], dtype=float)
    slots = np.asarray([event["slot"] for event in starts], dtype=float)
    scale = max(float(np.median(powers)), 0.5)
    features = np.column_stack([np.sin(2 * np.pi * slots / 96), np.cos(2 * np.pi * slots / 96), powers / scale])
    labels = DBSCAN(eps=0.55, min_samples=2).fit_predict(features)
    grouped: dict[int, list[dict]] = {}
    for label, event in zip(labels, starts):
        if label >= 0:
            grouped.setdefault(int(label), []).append(event)
    patterns = []
    for label, items in grouped.items():
        if len(items) >= 2:
            bucket = int(round(float(np.median([item["slot"] for item in items])))) % 96
            confidence = min(0.95, 0.5 + 0.06 * len(items) + 0.2 / (1 + float(np.std([item["slot"] for item in items]))))
            durations = [value for item in items if (value := _duration_for_start(item, events)) is not None]
            duration_slots = int(round(float(np.median(durations)))) if durations else 4
            estimated_power = round(sum(item["change_kw"] for item in items) / len(items), 2)
            patterns.append({
                "pattern_id": f"PAT-{label + 1:02d}",
                "typical_start_slot": bucket,
                "occurrences": len(items),
                "estimated_power_kw": estimated_power,
                "duration_slots": duration_slots,
                "duration_minutes": duration_slots * 15,
                "estimated_energy_kwh": round(estimated_power * duration_slots * 0.25, 2),
                "duration_observations": len(durations),
                "label": "Candidate recurring flexible-load event",
                "confidence": round(confidence, 2),
                "verification_status": "candidate",
                "method": "DBSCAN clustering of time-of-day and load-change magnitude",
            })
    return sorted(patterns, key=lambda item: item["typical_start_slot"])

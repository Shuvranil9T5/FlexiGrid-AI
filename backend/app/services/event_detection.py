import numpy as np
import pandas as pd

from app.services.clustering import cluster_start_events


def adaptive_thresholds(frame: pd.DataFrame, minimum_kw: float = 0.35, sensitivity: float = 1.0) -> pd.Series:
    """Return a robust local threshold from the median absolute deviation of load changes."""
    changes = frame["load_change"].abs()
    rolling_median = changes.rolling(24, min_periods=8).median()
    deviation = (changes - rolling_median).abs()
    rolling_mad = deviation.rolling(24, min_periods=8).median()
    global_median = float(changes.median())
    global_mad = float((changes - global_median).abs().median())
    rolling_median = rolling_median.fillna(global_median)
    rolling_mad = rolling_mad.fillna(max(global_mad, 0.05))
    return (rolling_median + (4.5 / sensitivity) * 1.4826 * rolling_mad).clip(lower=minimum_kw)


def _match_duration(start: dict, events: list[dict]) -> int | None:
    start_time = pd.Timestamp(start["timestamp"])
    for stop in events:
        if stop["event_type"] != "STOP":
            continue
        minutes = (pd.Timestamp(stop["timestamp"]) - start_time).total_seconds() / 60
        magnitude_ratio = abs(abs(stop["change_kw"]) - start["change_kw"]) / max(start["change_kw"], 0.1)
        if 15 <= minutes <= 480 and magnitude_ratio <= 0.45:
            return int(round(minutes / 15))
    return None


def detect_events(frame: pd.DataFrame, threshold_kw: float | None = None, sensitivity: float = 1.0) -> list[dict]:
    thresholds = pd.Series(float(threshold_kw), index=frame.index) if threshold_kw else adaptive_thresholds(frame, sensitivity=sensitivity)
    candidates = frame[frame["load_change"].abs() >= thresholds]
    events = []
    for timestamp, row in candidates.iterrows():
        threshold = float(thresholds.loc[timestamp])
        magnitude = abs(float(row["load_change"]))
        signal_ratio = magnitude / max(threshold, 0.01)
        events.append({
            "timestamp": timestamp.isoformat(),
            "slot": int(row["slot"]),
            "change_kw": round(float(row["load_change"]), 3),
            "event_type": "START" if row["load_change"] > 0 else "STOP",
            "confidence": round(min(0.99, 0.48 + 0.18 * signal_ratio), 2),
            "threshold_kw": round(threshold, 3),
            "threshold_mode": "manual" if threshold_kw else "adaptive MAD",
            "signal_to_threshold": round(signal_ratio, 2),
        })
    return events


def discover_patterns(events: list[dict]) -> list[dict]:
    grouped = cluster_start_events([event for event in events if event["event_type"] == "START"])
    patterns = []
    for label, items in grouped.items():
        slots = np.asarray([item["slot"] for item in items], dtype=float)
        powers = np.asarray([item["change_kw"] for item in items], dtype=float)
        durations = [value for item in items if (value := _match_duration(item, events)) is not None]
        duration_slots = int(round(float(np.median(durations)))) if durations else 4
        duration_spread = float(np.std(durations)) if durations else 1.0
        slot_spread = float(np.std(slots))
        power_mean, power_std = float(np.mean(powers)), float(np.std(powers))
        evidence_days = len({pd.Timestamp(item["timestamp"]).date() for item in items})
        confidence = min(0.97, 0.48 + 0.055 * len(items) + 0.18 / (1 + slot_spread) + 0.12 / (1 + power_std))
        patterns.append({
            "pattern_id": f"PAT-{label + 1:02d}",
            "typical_start_slot": int(round(float(np.median(slots)))) % 96,
            "occurrences": len(items),
            "evidence_days": evidence_days,
            "estimated_power_kw": round(power_mean, 2),
            "power_min_kw": round(max(0, power_mean - 1.96 * power_std), 2),
            "power_max_kw": round(power_mean + 1.96 * power_std, 2),
            "duration_slots": max(1, duration_slots),
            "duration_minutes": max(1, duration_slots) * 15,
            "duration_min_minutes": max(15, int(round((duration_slots - 1.96 * duration_spread) * 15))),
            "duration_max_minutes": max(15, int(round((duration_slots + 1.96 * duration_spread) * 15))),
            "start_uncertainty_minutes": max(15, int(round(slot_spread * 15))),
            "estimated_energy_kwh": round(power_mean * max(1, duration_slots) * 0.25, 2),
            "duration_observations": len(durations),
            "label": "Candidate recurring flexible-load event",
            "confidence": round(confidence, 2),
            "verification_status": "candidate",
            "method": "Adaptive MAD detection + DBSCAN recurrence clustering",
        })
    return sorted(patterns, key=lambda item: item["typical_start_slot"])

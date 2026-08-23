import pandas as pd

TIMESTAMP_ALIASES = {"timestamp", "datetime", "date_time", "time", "date"}
POWER_ALIASES = {"power_kw", "kw", "power", "load_kw", "demand_kw", "consumption_kw"}


def _normalise_columns(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    original = list(frame.columns)
    lowered = {str(column).strip().lower().replace(" ", "_"): column for column in frame.columns}
    timestamp = next((lowered[name] for name in TIMESTAMP_ALIASES if name in lowered), None)
    power = next((lowered[name] for name in POWER_ALIASES if name in lowered), None)
    if timestamp is None or power is None:
        raise ValueError(
            "CSV needs a time column (timestamp/datetime/time) and a power column "
            "(power_kw/kw/load_kw/demand_kw)"
        )
    renamed = frame.rename(columns={timestamp: "timestamp", power: "power_kw"})
    return renamed, {"original_columns": original, "timestamp_column": str(timestamp), "power_column": str(power)}


def prepare_readings(readings: list[dict]) -> tuple[pd.DataFrame, dict]:
    raw = pd.DataFrame(readings)
    if raw.empty:
        raise ValueError("The uploaded dataset is empty")
    frame, mapping = _normalise_columns(raw)
    input_rows = len(frame)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["power_kw"] = pd.to_numeric(frame["power_kw"], errors="coerce")
    invalid_rows = int(frame[["timestamp", "power_kw"]].isna().any(axis=1).sum())
    negative_rows = int((frame["power_kw"] < 0).fillna(False).sum())
    frame = frame.dropna(subset=["timestamp", "power_kw"])
    frame = frame[frame["power_kw"] >= 0].sort_values("timestamp")
    duplicate_rows = int(frame.duplicated("timestamp").sum())
    frame = frame.drop_duplicates("timestamp", keep="last")
    if frame.empty:
        raise ValueError("No valid non-negative power readings were found")
    if len(frame) < 8:
        raise ValueError("At least 8 valid readings are required")
    observed_rows = len(frame)
    frame = frame.set_index("timestamp").resample("15min").mean()
    missing_intervals = int(frame["power_kw"].isna().sum())
    frame["power_kw"] = frame["power_kw"].interpolate(limit=8, limit_direction="both")
    if frame["power_kw"].isna().any():
        raise ValueError("The dataset contains gaps longer than 2 hours; supply more complete data")
    q1, q3 = frame["power_kw"].quantile([0.25, 0.75])
    iqr = q3 - q1
    upper = q3 + 3 * iqr
    outlier_rows = int((frame["power_kw"] > upper).sum()) if iqr > 0 else 0
    if iqr > 0:
        frame["power_kw"] = frame["power_kw"].clip(upper=upper)
    frame["slot"] = frame.index.hour * 4 + frame.index.minute // 15
    frame["day_of_week"] = frame.index.dayofweek
    frame["load_change"] = frame["power_kw"].diff().fillna(0)
    frame["rolling_mean"] = frame["power_kw"].rolling(4, min_periods=1).mean()
    quality_score = max(0, round(100 * (1 - (invalid_rows + negative_rows + duplicate_rows + missing_intervals) / max(input_rows + missing_intervals, 1)), 1))
    report = {
        **mapping, "input_rows": input_rows, "valid_observed_rows": observed_rows,
        "output_15min_rows": len(frame), "invalid_rows_removed": invalid_rows,
        "negative_rows_removed": negative_rows, "duplicates_removed": duplicate_rows,
        "missing_intervals_interpolated": missing_intervals, "extreme_outliers_capped": outlier_rows,
        "quality_score": quality_score, "frequency": "15 minutes",
    }
    return frame, report


def readings_to_frame(readings: list[dict]) -> pd.DataFrame:
    return prepare_readings(readings)[0]


def serialise_frame(frame: pd.DataFrame) -> list[dict]:
    output = frame.reset_index()[["timestamp", "power_kw"]]
    output["timestamp"] = output["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    output["power_kw"] = output["power_kw"].round(3)
    return output.to_dict("records")

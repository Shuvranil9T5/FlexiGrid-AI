import numpy as np

from app.database import save_analysis
from app.ml.forecasting import forecast_with_evaluation
from app.services.demo_data import solar_profile, tariff_profile
from app.services.event_detection import detect_events, discover_patterns
from app.services.fault_detection import detect_faults
from app.services.passport_service import build_candidate_passports
from app.services.preprocessing import prepare_readings, serialise_frame


def analyse_readings(
    readings,
    threshold: float | None,
    source_label: str = "uploaded/measured as supplied",
    sensitivity: float = 1.0,
    forecast_models: list[str] | None = None,
) -> dict:
    frame, quality = prepare_readings(readings)

    events = detect_events(frame, threshold, sensitivity)
    patterns = discover_patterns(events)
    forecast = forecast_with_evaluation(frame, forecast_models)
    faults = detect_faults(frame, events, patterns)

    result = {
        "reading_count": len(frame),
        "readings": serialise_frame(frame),
        "events": events,
        "patterns": patterns,
        "candidate_passports": build_candidate_passports(patterns),
        "forecast_kw": forecast["forecast_kw"],
        "forecast_lower_kw": forecast["forecast_lower_kw"],
        "forecast_upper_kw": forecast["forecast_upper_kw"],
        "forecast_interval_confidence": forecast["interval_confidence"],
        "forecast_evaluation": forecast["evaluation"],
        "forecast_model": forecast["model"],
        "model_capabilities": forecast["model_capabilities"],
        "data_quality": quality,
        "source_label": source_label,
        "solar_kw": solar_profile(),
        "tariff": tariff_profile(),
        "fault_alerts": faults,
        "detection": {
            "mode": "manual" if threshold else "adaptive MAD",
            "manual_threshold_kw": threshold,
            "sensitivity": sensitivity,
            "median_threshold_kw": round(float(np.median([event["threshold_kw"] for event in events])), 3) if events else None,
        },
    }

    save_analysis(
        source_label,
        {
            "reading_count": len(frame),
            "event_count": len(events),
            "pattern_count": len(patterns),
            "forecast_model": forecast["model"],
            "fault_count": len([item for item in faults if item["severity"] != "info"]),
        },
    )

    return result

from app.database import save_analysis
from app.ml.forecasting import forecast_with_evaluation
from app.services.demo_data import solar_profile, tariff_profile
from app.services.event_detection import detect_events, discover_patterns
from app.services.passport_service import build_candidate_passports
from app.services.preprocessing import prepare_readings, serialise_frame


def analyse_readings(
    readings,
    threshold: float,
    source_label: str = "uploaded/measured as supplied",
) -> dict:
    frame, quality = prepare_readings(readings)

    events = detect_events(frame, threshold)
    patterns = discover_patterns(events)
    forecast = forecast_with_evaluation(frame)

    result = {
        "reading_count": len(frame),
        "readings": serialise_frame(frame),
        "events": events,
        "patterns": patterns,
        "candidate_passports": build_candidate_passports(patterns),
        "forecast_kw": forecast["forecast_kw"],
        "forecast_evaluation": forecast["evaluation"],
        "forecast_model": forecast["model"],
        "data_quality": quality,
        "source_label": source_label,
        "solar_kw": solar_profile(),
        "tariff": tariff_profile(),
    }

    save_analysis(
        source_label,
        {
            "reading_count": len(frame),
            "event_count": len(events),
            "pattern_count": len(patterns),
            "forecast_model": forecast["model"],
        },
    )

    return result
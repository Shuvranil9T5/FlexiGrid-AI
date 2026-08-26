from types import SimpleNamespace

from app.ml.forecasting import forecast_with_evaluation
from app.optimization.scheduler import optimize_schedule
from app.services.demo_data import generate_demo_readings
from app.services.event_detection import detect_events, discover_patterns
from app.services.fault_detection import detect_faults
from app.services.preprocessing import prepare_readings


def phase2_demo():
    frame, _ = prepare_readings(generate_demo_readings())
    events = detect_events(frame)
    patterns = discover_patterns(events)
    return frame, events, patterns


def test_adaptive_detection_exposes_threshold_evidence():
    _, events, patterns = phase2_demo()
    assert events and patterns
    assert all(event["threshold_mode"] == "adaptive MAD" for event in events)
    assert all(pattern["power_min_kw"] <= pattern["estimated_power_kw"] <= pattern["power_max_kw"] for pattern in patterns)


def test_forecast_has_ninety_percent_interval():
    frame, _, _ = phase2_demo()
    result = forecast_with_evaluation(frame)
    assert result["interval_confidence"] == 0.90
    assert len(result["forecast_lower_kw"]) == len(result["forecast_upper_kw"]) == 96
    assert all(low <= middle <= high for low, middle, high in zip(result["forecast_lower_kw"], result["forecast_kw"], result["forecast_upper_kw"]))


def test_fault_screening_always_returns_operator_message():
    frame, events, patterns = phase2_demo()
    alerts = detect_faults(frame, events, patterns)
    assert alerts and all({"code", "severity", "title", "description"} <= set(alert) for alert in alerts)


def test_optimizer_returns_four_counterfactual_scenarios():
    frame, _, patterns = phase2_demo()
    forecast = forecast_with_evaluation(frame)
    passports = []
    for pattern in patterns:
        payload = {**pattern,"label":"Verified load","earliest_start_slot":max(0,pattern["typical_start_slot"]-8),"latest_finish_slot":min(96,pattern["typical_start_slot"]+16),"priority":2,"interruptible":False,"minimum_runtime_slots":1,"criticality":"medium","notes":"","verified":True,"status":"confirmed"}
        passports.append(SimpleNamespace(**payload))
    result = optimize_schedule(forecast["forecast_kw"], passports, [0.0]*96, [4.5]*96, 20, "balanced", forecast["forecast_upper_kw"], True)
    assert result["solver_status"] in {"OPTIMAL", "FEASIBLE"}
    assert {scenario["mode"] for scenario in result["scenarios"]} == {"balanced", "cost", "peak", "carbon"}

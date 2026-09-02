from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "healthy"


def test_demo_has_672_readings():
    response = client.get("/api/demo")
    assert response.status_code == 200
    assert response.json()["reading_count"] == 672
    assert response.json()["forecast_evaluation"]["status"] == "measured"
    assert response.json()["source_label"] == "simulated"


def test_upload_accepts_common_column_aliases():
    csv = "datetime,load_kw\n" + "\n".join(f"2026-08-01T{hour:02d}:{minute:02d}:00,2.5" for hour in range(2) for minute in (0, 15, 30, 45))
    response = client.post("/api/upload", files={"file": ("meter.csv", csv, "text/csv")})
    assert response.status_code == 200
    assert response.json()["data_quality"]["power_column"] == "load_kw"


def test_optimizer_with_no_passports_keeps_baseline():
    demo = client.get("/api/demo").json()
    response = client.post("/api/optimize", json={"forecast_kw": demo["forecast_kw"], "solar_kw": demo["solar_kw"], "tariff": demo["tariff"], "passports": [], "max_building_kw": 20, "mode": "balanced"})
    assert response.status_code == 200
    assert response.json()["optimized_load_kw"] == response.json()["baseline_load_kw"]


def test_demo_compares_forecast_models_and_infers_duration():
    data = client.get("/api/demo").json()
    assert {"Seasonal baseline", "Random Forest", "LightGBM"} == set(data["forecast_evaluation"]["models"])
    assert data["model_capabilities"]["LightGBM"]["available"] is True
    assert all(pattern["duration_slots"] >= 1 for pattern in data["patterns"])


def test_passport_workflow_uses_numeric_pattern_order():
    passports = client.get("/api/demo").json()["candidate_passports"]
    identifiers = [passport["pattern_id"] for passport in passports]
    assert identifiers == sorted(identifiers, key=lambda value: int(value.split("-")[-1]))


def test_real_dataset_catalog_has_uci_and_iblend_samples():
    response = client.get("/api/datasets")
    assert response.status_code == 200
    datasets = {item["id"]: item for item in response.json()["datasets"]}
    assert set(datasets) == {"uci", "iblend"}
    assert datasets["uci"]["native_resolution"] == "15 minutes"
    assert datasets["iblend"]["sample_available"] is True


def test_model_status_distinguishes_advanced_models():
    models = client.get("/api/models/status").json()["models"]
    assert models["LightGBM"]["type"] == "advanced gradient boosting"
    assert models["TFT"]["type"] == "advanced deep learning"


def test_report_download_is_pdf():
    result = {"mode":"balanced", "before":{}, "after":{}, "differences":{}, "schedule":[], "constraint_violations":0}
    response = client.post("/api/report", json={"result":result, "source_label":"simulated"})
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")

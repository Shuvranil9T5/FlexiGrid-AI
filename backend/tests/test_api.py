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
    assert {"Seasonal baseline", "Random Forest"} == set(data["forecast_evaluation"]["models"])
    assert all(pattern["duration_slots"] >= 1 for pattern in data["patterns"])


def test_report_download_is_pdf():
    result = {"mode":"balanced", "before":{}, "after":{}, "differences":{}, "schedule":[], "constraint_violations":0}
    response = client.post("/api/report", json={"result":result, "source_label":"simulated"})
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")

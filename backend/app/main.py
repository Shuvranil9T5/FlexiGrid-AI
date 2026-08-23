from io import BytesIO
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

from app.ml.forecasting import forecast_next_day, forecast_with_evaluation
from app.optimization.scheduler import optimize_schedule
from app.schemas import AnalysisRequest, FlexibilityPassport, ForecastRequest, OptimizationRequest, OptimizationReportRequest
from app.database import init_db, list_saved_passports, save_passport_record, save_run
from app.report import build_optimization_report
from app.services.demo_data import generate_demo_readings, solar_profile, tariff_profile
from app.services.event_detection import detect_events, discover_patterns
from app.services.preprocessing import prepare_readings, readings_to_frame, serialise_frame

app = FastAPI(title="FlexiGrid AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
init_db()

PASSPORTS: dict[str, dict] = {}


def analyse(readings, threshold=0.8, source_label="uploaded/measured as supplied"):
    frame, quality = prepare_readings(readings)
    events = detect_events(frame, threshold)
    forecast = forecast_with_evaluation(frame)
    patterns = discover_patterns(events)
    saved = {item["pattern_id"]: item for item in list_saved_passports()}
    candidate_passports = []
    for pattern in patterns:
        generated = {
            **pattern, "label": "User-defined candidate load",
            "earliest_start_slot": max(0, pattern["typical_start_slot"] - 8),
            "latest_finish_slot": min(96, pattern["typical_start_slot"] + 16),
            "priority": 2, "interruptible": False, "minimum_runtime_slots": 1,
            "criticality": "medium", "notes": "", "verified": False, "status": "candidate",
        }
        if pattern["pattern_id"] in saved:
            generated.update(saved[pattern["pattern_id"]])
            generated.update({key: pattern[key] for key in ("occurrences", "confidence", "duration_observations")})
        candidate_passports.append(generated)
    return {
        "reading_count": len(frame),
        "readings": serialise_frame(frame),
        "events": events,
        "patterns": patterns,
        "candidate_passports": candidate_passports,
        "forecast_kw": forecast["forecast_kw"],
        "forecast_evaluation": forecast["evaluation"],
        "forecast_model": forecast["model"],
        "data_quality": quality,
        "source_label": source_label,
        "solar_kw": solar_profile(),
        "tariff": tariff_profile(),
    }


@app.get("/")
def root():
    return {"message": "FlexiGrid AI backend is running", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}


@app.get("/api/demo")
def demo():
    return analyse(generate_demo_readings(), source_label="simulated")


@app.post("/api/analyse")
def analyse_json(request: AnalysisRequest):
    try:
        return analyse([item.model_dump() for item in request.readings], request.event_threshold_kw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), event_threshold_kw: float = 0.8):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file")
    try:
        raw = await file.read()
        frame = pd.read_csv(BytesIO(raw))
        return analyse(frame.to_dict("records"), event_threshold_kw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not process CSV: {exc}") from exc


@app.post("/api/passports")
def save_passport(passport: FlexibilityPassport):
    payload = passport.model_dump()
    payload["verified"] = payload["status"] == "confirmed"
    PASSPORTS[passport.pattern_id] = payload
    save_passport_record(payload)
    return payload


@app.get("/api/passports")
def list_passports():
    return list_saved_passports()


@app.post("/api/forecast")
def forecast(request: ForecastRequest):
    frame = readings_to_frame([item.model_dump() for item in request.readings])
    return {"forecast_kw": forecast_next_day(frame)}


@app.post("/api/optimize")
def optimize(request: OptimizationRequest):
    result = optimize_schedule(
        request.forecast_kw,
        request.passports,
        request.solar_kw,
        request.tariff,
        request.max_building_kw,
        request.mode,
    )
    save_run(request.mode, result)
    return result

@app.post("/api/report")
def optimization_report(request: OptimizationReportRequest):
    pdf = build_optimization_report(request.result, request.source_label)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition":"attachment; filename=FlexiGrid-Optimization-Report.pdf"})

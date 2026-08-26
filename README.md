# FlexiGrid AI Phase 2.0

FlexiGrid AI is a software-first energy-flexibility MVP. It accepts aggregate 15-minute power readings, discovers candidate recurring events, creates user-verified Flexibility Passports, forecasts the next 24 hours, and produces a constrained schedule.

Phase 2.0 adds adaptive MAD event thresholds, uncertainty-aware Passports, 90% forecast intervals, OR-Tools CP-SAT scheduling, editable time-of-day tariffs, four counterfactual digital-twin scenarios, and statistical energy-waste/fault screening.

The included demo contains 672 readings: 7 days × 24 hours × 4 readings/hour.

## 1. Start the backend (macOS)

```bash
cd FlexiGrid-AI/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload
```

API: http://127.0.0.1:8000

Swagger: http://127.0.0.1:8000/docs

## 2. Start the frontend

In a second Terminal:

```bash
cd FlexiGrid-AI/frontend
npm install
npm run dev
```

Open http://localhost:5173

## 3. Run the demo

Click **Load 7-Day Demo**. The dashboard requests 672 simulated readings from the backend, detects candidate events, forecasts the next day, and creates candidate Flexibility Passports. Review each Passport, confirm at least one non-critical load, edit the tariff if needed, and click **Run Robust Optimization**.

## How Phase 2.0 works

1. The preprocessing service validates timestamps and power, removes invalid rows, resamples to 15-minute intervals, fills short gaps, and reports a data-quality score.
2. Adaptive event detection uses a rolling median absolute deviation threshold, so normal meter noise is treated differently from a meaningful load change.
3. DBSCAN groups repeated start events by time of day and power. Each candidate includes power, duration, start-time uncertainty, evidence days, and confidence.
4. A person names, edits, confirms, or rejects every Flexibility Passport. Critical and unconfirmed loads are never scheduled.
5. The forecasting service compares a seasonal baseline with Random Forest on the last historical day and produces a 90% prediction interval.
6. OR-Tools CP-SAT schedules confirmed loads against the upper forecast bound, the edited tariff, solar availability, operating windows, and the building-demand limit.
7. Balanced, lowest-cost, lowest-peak, and carbon-aware scenarios are calculated from the same verified inputs and displayed side by side.
8. Statistical fault screening highlights unusual spikes, high off-hours baseload, rising daily baseload, and incomplete operating cycles for operator review.

## Main code structure

- `backend/app/services/` — preprocessing, adaptive event discovery, Passport generation, and fault screening.
- `backend/app/ml/` — forecasting and chronological model evaluation.
- `backend/app/optimization/` — robust CP-SAT scheduling and scenario comparison.
- `backend/app/routers/` — FastAPI endpoints used by the dashboard.
- `frontend/src/components/` — charts, tariff editor, uncertainty, scenarios, and fault alerts.
- `frontend/src/App.jsx` — the human-review workflow that connects analysis to optimization.

## CSV format

```csv
timestamp,power_kw
2026-08-01T00:00:00,2.45
```

## Important interpretation

The event detector discovers candidate load events from aggregate readings. It does not claim exact appliance identification. A person verifies a pattern before it becomes a schedulable Flexibility Passport.

## Main API endpoints

- `GET /api/health`
- `GET /api/demo`
- `POST /api/analyse`
- `POST /api/upload`
- `POST /api/passports`
- `GET /api/passports`
- `POST /api/forecast`
- `POST /api/optimize`

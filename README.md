# FlexiGrid AI MVP

FlexiGrid AI is a software-first energy-flexibility MVP. It accepts aggregate 15-minute power readings, discovers candidate recurring events, creates user-verified Flexibility Passports, forecasts the next 24 hours, and produces a constrained schedule.

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

Click **Load 7-Day Demo**. The dashboard requests 672 simulated readings from the backend, detects candidate events, forecasts the next day, creates sample verified passports, runs the optimizer, and displays the original and recommended schedules.

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


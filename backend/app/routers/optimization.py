from fastapi import APIRouter
from app.database import save_run
from app.optimization.scheduler import optimize_schedule
from app.schemas import OptimizationRequest
router = APIRouter(prefix="/api", tags=["optimization"])

@router.post("/optimize")
def optimize(request: OptimizationRequest):
    result = optimize_schedule(request.forecast_kw, request.passports, request.solar_kw, request.tariff, request.max_building_kw, request.mode, request.forecast_upper_kw, request.include_scenarios)
    save_run(request.mode, result); return result

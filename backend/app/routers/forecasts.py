from fastapi import APIRouter
from app.ml.forecasting import forecast_with_evaluation
from app.schemas import ForecastRequest
from app.services.preprocessing import readings_to_frame
router = APIRouter(prefix="/api", tags=["forecast"])

@router.post("/forecast")
def forecast(request: ForecastRequest): return forecast_with_evaluation(readings_to_frame([item.model_dump() for item in request.readings]))

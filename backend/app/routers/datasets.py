from fastapi import APIRouter, HTTPException

from app.config import settings
from app.ml.forecasting import model_capabilities
from app.services.analysis_service import analyse_readings
from app.services.dataset_service import dataset_catalog, load_sample


router = APIRouter(prefix="/api", tags=["real datasets and models"])


@router.get("/datasets")
def datasets():
    return {"datasets": dataset_catalog()}


@router.get("/datasets/{dataset_id}/sample")
def analyse_dataset_sample(dataset_id: str):
    try:
        readings, metadata = load_sample(dataset_id)
        models = ["Seasonal baseline", "Random Forest", "LightGBM"]
        if dataset_id.lower() == "uci":
            # The bundled demonstration checkpoint is trained on UCI MT_001.
            # A site-specific I-BLEND checkpoint can be trained with train_tft.py.
            models.append("TFT")
        return analyse_readings(
            readings,
            settings.default_event_threshold_kw,
            source_label=f"real sample · {metadata['name']} · {metadata['sample_series']}",
            forecast_models=models,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/models/status")
def models_status():
    return {"models": model_capabilities()}

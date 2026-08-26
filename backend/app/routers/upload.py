from io import BytesIO

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas import AnalysisRequest
from app.services.analysis_service import analyse_readings
from app.services.demo_data import generate_demo_readings


router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/demo")
def demo():
    return analyse_readings(
        generate_demo_readings(),
        None,
        "simulated",
    )


@router.post("/analyse")
def analyse_json(request: AnalysisRequest):
    try:
        readings = [item.model_dump() for item in request.readings]

        return analyse_readings(
            readings,
            request.event_threshold_kw,
            sensitivity=request.detection_sensitivity,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    event_threshold_kw: float | None = None,
    detection_sensitivity: float = 1.0,
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Upload a CSV file",
        )

    try:
        raw_file = await file.read()
        dataframe = pd.read_csv(BytesIO(raw_file))
        readings = dataframe.to_dict("records")

        return analyse_readings(
            readings,
            event_threshold_kw,
            sensitivity=detection_sensitivity,
        )

    except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CSV file: {exc}",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected CSV processing error: {exc}",
        ) from exc

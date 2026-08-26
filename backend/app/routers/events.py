from fastapi import APIRouter
from app.schemas import EventDetectionRequest
from app.services.event_detection import detect_events, discover_patterns
from app.services.preprocessing import readings_to_frame
router = APIRouter(prefix="/api/events", tags=["events"])

@router.post("/detect")
def detect(request: EventDetectionRequest):
    events = detect_events(readings_to_frame([item.model_dump() for item in request.readings]), request.event_threshold_kw, request.detection_sensitivity)
    return {"events": events, "patterns": discover_patterns(events)}

from fastapi import APIRouter
from fastapi.responses import Response
from app.report import build_optimization_report
from app.schemas import OptimizationReportRequest
router = APIRouter(prefix="/api", tags=["reports"])

@router.post("/report")
def optimization_report(request: OptimizationReportRequest):
    pdf = build_optimization_report(request.result, request.source_label)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition":"attachment; filename=FlexiGrid-Optimization-Report.pdf"})

from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def build_optimization_report(result: dict, source_label: str) -> bytes:
    stream = BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    story = [Paragraph("FlexiGrid AI - Optimization Report", styles["Title"]), Paragraph(f"Result type: {source_label}. Values are forecasts or simulated estimates, not measured savings.", styles["BodyText"]), Spacer(1, 8)]
    before, after = result.get("before", {}), result.get("after", {})
    rows = [["Metric", "Before", "After", "Difference"]]
    for key, label in {"peak_kw":"Peak demand (kW)", "energy_cost_units":"Energy cost (units)", "solar_used_kwh":"Solar used (kWh)"}.items():
        rows.append([label, before.get(key,"-"), after.get(key,"-"), result.get("differences",{}).get(key,"-")])
    table = Table(rows, colWidths=[68*mm,30*mm,30*mm,30*mm])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0f766e")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.5,colors.grey),("PADDING",(0,0),(-1,-1),7)]))
    story += [table, Spacer(1,14), Paragraph("Recommendations", styles["Heading2"])]
    if not result.get("schedule"):
        story.append(Paragraph("No feasible verified load shift was found.", styles["BodyText"]))
    for item in result.get("schedule",[]):
        story += [Paragraph(f"{item.get('label',item.get('pattern_id'))}: {item.get('original_time')} to {item.get('recommended_time')}", styles["Heading3"]), Paragraph(item.get("explanation",item.get("reason","")), styles["BodyText"]), Spacer(1,6)]
    story += [Spacer(1,10), Paragraph(f"Mode: {result.get('mode','balanced').title()} | Constraint violations: {result.get('constraint_violations',0)}", styles["BodyText"])]
    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(18*mm, 10*mm, "FlexiGrid AI | Recommendation-only decision support")
        canvas.drawRightString(192*mm, 10*mm, f"Page {document.page}")
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()

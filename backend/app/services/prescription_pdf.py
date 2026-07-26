from io import BytesIO

from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.models import Visit


def build_prescription_pdf(visit: Visit) -> StreamingResponse:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 25 * mm
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(25 * mm, y, "AI ClinicOS")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(25 * mm, y - 6 * mm, "Intelligent AI-Powered Clinic Management System")
    pdf.line(25 * mm, y - 12 * mm, width - 25 * mm, y - 12 * mm)

    y -= 25 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(25 * mm, y, "Patient")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(25 * mm, y - 6 * mm, f"{visit.patient.name} ({visit.patient.patient_code})")
    pdf.drawString(25 * mm, y - 12 * mm, f"Age/Gender: {visit.patient.age or '-'} / {visit.patient.gender or '-'}")
    pdf.drawString(115 * mm, y, f"Doctor: {visit.doctor.full_name}")
    pdf.drawString(115 * mm, y - 6 * mm, f"Date: {visit.created_at:%d %b %Y}")

    y -= 28 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(25 * mm, y, "Diagnosis")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(25 * mm, y - 6 * mm, (visit.diagnosis or "Pending doctor review")[:100])

    y -= 20 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(25 * mm, y, "Prescription")
    y -= 8 * mm
    pdf.setFont("Helvetica", 9)
    for idx, item in enumerate(visit.prescription_items, start=1):
        line = f"{idx}. {item.medicine_name} - {item.dosage}, {item.frequency}, {item.duration}"
        pdf.drawString(25 * mm, y, line[:120])
        y -= 5 * mm
        if item.instructions:
            pdf.drawString(31 * mm, y, f"Instructions: {item.instructions}"[:120])
            y -= 5 * mm
        if y < 35 * mm:
            pdf.showPage()
            y = height - 25 * mm

    pdf.setFont("Helvetica", 9)
    pdf.drawString(25 * mm, 25 * mm, "AI assistance is advisory only. Final prescription reviewed and approved by the doctor.")
    pdf.drawString(135 * mm, 40 * mm, "Doctor Signature")
    pdf.line(135 * mm, 37 * mm, 185 * mm, 37 * mm)
    pdf.save()
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=prescription-{visit.id}.pdf"},
    )

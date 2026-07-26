from datetime import date, datetime, time, timedelta
from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Appointment, Medicine, Role, User, Visit
from app.services.medicine_importer import EXPECTED_COLUMNS


router = APIRouter()


def period_bounds(period: str) -> tuple[datetime, datetime]:
    today = date.today()
    if period == "weekly":
        start_day = today - timedelta(days=today.weekday())
        end_day = start_day + timedelta(days=7)
    elif period == "monthly":
        start_day = today.replace(day=1)
        end_day = (start_day + timedelta(days=32)).replace(day=1)
    else:
        start_day = today
        end_day = today + timedelta(days=1)
    return datetime.combine(start_day, time.min), datetime.combine(end_day, time.min)


@router.get("/summary")
def report_summary(period: str = "daily", db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor, Role.nurse))):
    start, end = period_bounds(period)
    visits = db.scalars(select(Visit).where(Visit.created_at >= start, Visit.created_at < end)).all()
    appointments = db.scalars(select(Appointment).where(Appointment.appointment_at >= start, Appointment.appointment_at < end)).all()
    return {
        "period": period,
        "visits": len(visits),
        "appointments": len(appointments),
        "diagnoses": [{"patient": visit.patient.name, "diagnosis": visit.diagnosis, "date": visit.created_at} for visit in visits],
    }


@router.get("/medicines.xlsx")
def medicines_excel(db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor, Role.nurse))):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Medicine Usage"
    headers = list(EXPECTED_COLUMNS)
    sheet.append(headers)
    for med in db.scalars(select(Medicine).order_by(Medicine.medicine_name)):
        sheet.append([getattr(med, EXPECTED_COLUMNS[header]) for header in headers])
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=medicine-report.xlsx"})


@router.get("/summary.pdf")
def summary_pdf(period: str = "daily", db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor, Role.nurse))):
    data = report_summary(period, db, _)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = 800
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "AI ClinicOS Report")
    pdf.setFont("Helvetica", 11)
    y -= 30
    pdf.drawString(50, y, f"Period: {data['period']}")
    y -= 20
    pdf.drawString(50, y, f"Visits: {data['visits']}   Appointments: {data['appointments']}")
    y -= 30
    for item in data["diagnoses"][:30]:
        pdf.drawString(50, y, f"{item['date']:%d %b %Y} - {item['patient']} - {item['diagnosis'] or 'Diagnosis pending'}"[:95])
        y -= 16
    pdf.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={period}-report.pdf"})

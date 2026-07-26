from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Appointment, AppointmentStatus, Medicine, Patient, PatientDocument, PrescriptionItem, Role, User, Visit
from app.schemas import DashboardStats


router = APIRouter()


def day_bounds(target: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target, time.min)
    return start, start + timedelta(days=1)


def count_scalar(db: Session, stmt) -> int:
    return int(db.scalar(stmt) or 0)


def doctor_scope(user: User):
    return [Appointment.doctor_id == user.id] if user.role == Role.doctor else []


def visit_doctor_scope(user: User):
    return [Visit.doctor_id == user.id] if user.role == Role.doctor else []


def date_label(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


@router.get("", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor, Role.nurse))):
    start, end = day_bounds(date.today())
    todays_patients = db.scalar(select(func.count(Visit.id)).where(Visit.created_at >= start, Visit.created_at < end)) or 0
    appointments = db.scalar(select(func.count(Appointment.id)).where(Appointment.appointment_at >= start, Appointment.appointment_at < end)) or 0
    pending_followups = db.scalar(select(func.count(Appointment.id)).where(Appointment.follow_up_required.is_(True), Appointment.status == AppointmentStatus.waiting)) or 0
    medicine_stock = db.scalar(select(func.coalesce(func.sum(Medicine.stock_quantity), 0))) or 0
    return DashboardStats(
        todays_patients=todays_patients,
        appointments=appointments,
        pending_followups=pending_followups,
        medicine_stock=medicine_stock,
        revenue=0.0,
    )


@router.get("/recent-patients")
def recent_patients(db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor, Role.nurse))):
    patients = db.scalars(select(Patient).order_by(Patient.created_at.desc()).limit(8)).all()
    return [
        {
            "id": patient.id,
            "patient_code": patient.patient_code,
            "name": patient.name,
            "phone": patient.phone,
            "age": patient.age,
            "gender": patient.gender,
            "registration_date": patient.created_at,
        }
        for patient in patients
    ]


@router.get("/live")
def live_dashboard(db: Session = Depends(get_db), user: User = Depends(require_role(Role.doctor, Role.nurse))):
    today = date.today()
    start, end = day_bounds(today)
    month_start = today.replace(day=1)
    week_start = today - timedelta(days=today.weekday())
    last_7_start = today - timedelta(days=6)
    last_30_start = today - timedelta(days=29)

    total_patients = count_scalar(db, select(func.count(Patient.id)))
    todays_new_patients = count_scalar(db, select(func.count(Patient.id)).where(Patient.created_at >= start, Patient.created_at < end))
    total_medicines = count_scalar(db, select(func.count(Medicine.id)))
    uploaded_lab_reports = count_scalar(
        db,
        select(func.count(PatientDocument.id)).where(
            func.lower(PatientDocument.document_type).like("%lab%") | func.lower(PatientDocument.document_type).like("%report%")
        ),
    )
    pending_registrations = count_scalar(db, select(func.count(Patient.id)).where(~Patient.id.in_(select(Visit.patient_id))))

    appointment_today = [Appointment.appointment_at >= start, Appointment.appointment_at < end, *doctor_scope(user)]
    completed_today = [*appointment_today, Appointment.status == AppointmentStatus.completed]
    waiting_today = [*appointment_today, Appointment.status == AppointmentStatus.waiting]

    stats = {
        "total_patients": total_patients,
        "todays_new_patients": todays_new_patients,
        "todays_appointments": count_scalar(db, select(func.count(Appointment.id)).where(*appointment_today)),
        "waiting_appointments": count_scalar(db, select(func.count(Appointment.id)).where(*waiting_today)),
        "completed_appointments_today": count_scalar(db, select(func.count(Appointment.id)).where(*completed_today)),
        "total_medicines": total_medicines,
        "todays_consultations": count_scalar(db, select(func.count(Visit.id)).where(Visit.created_at >= start, Visit.created_at < end, *visit_doctor_scope(user))),
        "pending_followups": count_scalar(db, select(func.count(Appointment.id)).where(Appointment.follow_up_required.is_(True), Appointment.status == AppointmentStatus.waiting, *doctor_scope(user))),
        "ai_recommendations_today": count_scalar(db, select(func.count(Visit.id)).where(Visit.created_at >= start, Visit.created_at < end, Visit.ai_summary.is_not(None), Visit.ai_summary != "", *visit_doctor_scope(user))),
        "uploaded_lab_reports": uploaded_lab_reports,
        "follow_up_patients": count_scalar(db, select(func.count(Appointment.id)).where(Appointment.follow_up_required.is_(True), *doctor_scope(user))),
        "pending_registrations": pending_registrations,
    }

    summary = {
        "new_patients": todays_new_patients,
        "appointments_booked": stats["todays_appointments"],
        "consultations_completed": stats["todays_consultations"],
        "prescriptions_generated": count_scalar(db, select(func.count(PrescriptionItem.id)).join(Visit).where(Visit.created_at >= start, Visit.created_at < end, *visit_doctor_scope(user))),
        "medicines_added": 0,
    }

    monthly_rows = db.execute(
        select(func.extract("month", Patient.created_at), func.count(Patient.id))
        .where(func.extract("year", Patient.created_at) == today.year)
        .group_by(func.extract("month", Patient.created_at))
    ).all()
    monthly_counts = {int(month): int(count) for month, count in monthly_rows}

    daily_appointment_rows = db.execute(
        select(func.date(Appointment.appointment_at), func.count(Appointment.id))
        .where(Appointment.appointment_at >= datetime.combine(last_7_start, time.min), Appointment.appointment_at < end, *doctor_scope(user))
        .group_by(func.date(Appointment.appointment_at))
    ).all()
    daily_appointments = {date_label(day): int(count) for day, count in daily_appointment_rows}

    status_rows = db.execute(
        select(Appointment.status, func.count(Appointment.id)).where(*doctor_scope(user)).group_by(Appointment.status)
    ).all()
    status_counts = {status.value if hasattr(status, "value") else str(status): int(count) for status, count in status_rows}

    disease_rows = db.execute(
        select(Visit.diagnosis, func.count(Visit.id))
        .where(Visit.diagnosis.is_not(None), Visit.diagnosis != "", *visit_doctor_scope(user))
        .group_by(Visit.diagnosis)
        .order_by(func.count(Visit.id).desc())
        .limit(10)
    ).all()

    medicine_rows = db.execute(
        select(PrescriptionItem.medicine_name, func.count(PrescriptionItem.id))
        .join(Visit)
        .where(PrescriptionItem.medicine_name.is_not(None), PrescriptionItem.medicine_name != "", *visit_doctor_scope(user))
        .group_by(PrescriptionItem.medicine_name)
        .order_by(func.count(PrescriptionItem.id).desc())
        .limit(10)
    ).all()

    weekly_rows = db.execute(
        select(func.date(Visit.created_at), func.count(Visit.id))
        .where(Visit.created_at >= datetime.combine(week_start, time.min), Visit.created_at < datetime.combine(week_start + timedelta(days=7), time.min), *visit_doctor_scope(user))
        .group_by(func.date(Visit.created_at))
    ).all()
    weekly_consultations = {date_label(day): int(count) for day, count in weekly_rows}

    followup_rows = db.execute(
        select(Appointment.status, func.count(Appointment.id))
        .where(Appointment.follow_up_required.is_(True), *doctor_scope(user))
        .group_by(Appointment.status)
    ).all()
    followup_counts = {status.value if hasattr(status, "value") else str(status): int(count) for status, count in followup_rows}

    ai_rows = db.execute(
        select(func.date(Visit.created_at), func.count(Visit.id))
        .where(
            Visit.created_at >= datetime.combine(last_30_start, time.min),
            Visit.created_at < end,
            Visit.ai_summary.is_not(None),
            Visit.ai_summary != "",
            *visit_doctor_scope(user),
        )
        .group_by(func.date(Visit.created_at))
    ).all()
    ai_activity = {date_label(day): int(count) for day, count in ai_rows}

    recent_patients_rows = db.scalars(select(Patient).order_by(Patient.created_at.desc()).limit(8)).all()
    todays_appointments_rows = db.scalars(
        select(Appointment).where(*appointment_today).order_by(Appointment.appointment_at.asc()).limit(10)
    ).all()
    prescription_rows = db.execute(
        select(PrescriptionItem, Visit, Patient, User)
        .join(Visit, PrescriptionItem.visit_id == Visit.id)
        .join(Patient, Visit.patient_id == Patient.id)
        .join(User, Visit.doctor_id == User.id)
        .where(*visit_doctor_scope(user))
        .order_by(Visit.created_at.desc())
        .limit(10)
    ).all()

    activity = []
    for patient in recent_patients_rows[:5]:
        activity.append({"time": patient.created_at, "user": "Clinic staff", "action": "New patient registered", "patient": patient.name})
    for appointment in db.scalars(select(Appointment).order_by(Appointment.created_at.desc()).limit(5)):
        activity.append({"time": appointment.created_at, "user": appointment.booked_by.full_name if appointment.booked_by else "Clinic staff", "action": "Appointment booked", "patient": appointment.patient.name})
        if appointment.status == AppointmentStatus.completed:
            activity.append({"time": appointment.updated_at or appointment.created_at, "user": appointment.doctor.full_name if appointment.doctor else "Doctor", "action": "Appointment completed", "patient": appointment.patient.name})
    for document in db.scalars(select(PatientDocument).order_by(PatientDocument.uploaded_at.desc()).limit(5)):
        activity.append({"time": document.uploaded_at, "user": document.uploaded_by.full_name if document.uploaded_by else "Clinic staff", "action": "Lab report uploaded", "patient": document.patient.name})
    for item, visit, patient, doctor in prescription_rows[:5]:
        activity.append({"time": visit.created_at, "user": doctor.full_name, "action": "Prescription generated", "patient": patient.name})
    activity.sort(key=lambda item: item["time"] or datetime.min, reverse=True)

    return {
        "role": user.role.value,
        "stats": stats,
        "summary": summary,
        "charts": {
            "monthly_patient_registrations": [{"label": date(today.year, month, 1).strftime("%B"), "value": monthly_counts.get(month, 0)} for month in range(1, 13)],
            "daily_appointments": [
                {"label": (last_7_start + timedelta(days=offset)).strftime("%d %b"), "value": daily_appointments.get((last_7_start + timedelta(days=offset)).isoformat(), 0)}
                for offset in range(7)
            ],
            "appointment_status_distribution": [
                {"label": label, "value": status_counts.get(status, 0)}
                for status, label in [("waiting", "Waiting"), ("in_progress", "In Progress"), ("completed", "Completed"), ("cancelled", "Cancelled")]
            ],
            "common_diseases": [{"label": diagnosis, "value": int(count)} for diagnosis, count in disease_rows],
            "medicine_usage": [{"label": name, "value": int(count)} for name, count in medicine_rows],
            "weekly_consultations": [
                {"label": (week_start + timedelta(days=offset)).strftime("%A"), "value": weekly_consultations.get((week_start + timedelta(days=offset)).isoformat(), 0)}
                for offset in range(7)
            ],
            "followup_status": [
                {"label": "Completed", "value": followup_counts.get("completed", 0)},
                {"label": "Pending", "value": followup_counts.get("waiting", 0) + followup_counts.get("in_progress", 0) + followup_counts.get("scheduled", 0)},
                {"label": "Missed", "value": followup_counts.get("missed", 0) + followup_counts.get("cancelled", 0)},
            ],
            "ai_recommendation_activity": [
                {"label": (last_30_start + timedelta(days=offset)).strftime("%d %b"), "value": ai_activity.get((last_30_start + timedelta(days=offset)).isoformat(), 0)}
                for offset in range(30)
            ],
        },
        "tables": {
            "recent_patients": [
                {
                    "id": patient.id,
                    "patient_code": patient.patient_code,
                    "name": patient.name,
                    "age": patient.age,
                    "gender": patient.gender,
                    "registration_date": patient.created_at,
                }
                for patient in recent_patients_rows
            ],
            "todays_appointments": [
                {
                    "token": appointment.token_number,
                    "patient": appointment.patient.name,
                    "time": appointment.appointment_time,
                    "status": appointment.status.value,
                }
                for appointment in todays_appointments_rows
            ],
            "recent_prescriptions": [
                {
                    "patient": patient.name,
                    "medicine": item.medicine_name,
                    "doctor": doctor.full_name,
                    "date": visit.created_at,
                }
                for item, visit, patient, doctor in prescription_rows
            ],
        },
        "activity": [
            {
                "time": item["time"],
                "user": item["user"],
                "action": item["action"],
                "patient": item["patient"],
            }
            for item in activity[:12]
        ],
    }

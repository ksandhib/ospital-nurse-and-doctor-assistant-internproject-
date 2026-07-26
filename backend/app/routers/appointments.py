from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Appointment, AppointmentStatus, Patient, PrescriptionItem, Role, User, Visit
from app.schemas import (
    AppointmentComplete,
    AppointmentCreate,
    AppointmentNotification,
    AppointmentRead,
    AppointmentSummary,
    AppointmentUpdate,
)


router = APIRouter()


def day_bounds(target: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target, time.min)
    return start, start + timedelta(days=1)


def appointment_to_read(appointment: Appointment) -> AppointmentRead:
    return AppointmentRead(
        id=appointment.id,
        token_number=appointment.token_number,
        patient_id=appointment.patient_id,
        patient_code=appointment.patient.patient_code,
        patient_name=appointment.patient.name,
        doctor_id=appointment.doctor_id,
        doctor_name=appointment.doctor.full_name if appointment.doctor else None,
        appointment_at=appointment.appointment_at,
        appointment_date=appointment.appointment_date,
        appointment_time=appointment.appointment_time,
        visit_type=appointment.visit_type,
        priority=appointment.priority,
        reason_for_visit=appointment.reason_for_visit or appointment.reason,
        notes=appointment.notes,
        status=appointment.status,
        follow_up_required=appointment.follow_up_required,
    )


def next_token_number(db: Session, appointment_date: date) -> str:
    start, end = day_bounds(appointment_date)
    count = db.scalar(select(func.count(Appointment.id)).where(Appointment.appointment_at >= start, Appointment.appointment_at < end)) or 0
    return f"T{count + 1:03d}"


def scoped_query(user: User):
    stmt = select(Appointment)
    if user.role == Role.doctor:
        stmt = stmt.where(Appointment.doctor_id == user.id)
    return stmt


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    q: str | None = None,
    doctor_id: int | None = None,
    status: AppointmentStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    view: str = Query(default="day", pattern="^(day|week|month|all)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.doctor, Role.nurse)),
):
    stmt = scoped_query(user).join(Patient).outerjoin(User, Appointment.doctor_id == User.id)
    today = date.today()
    if date_from:
        start = datetime.combine(date_from, time.min)
        stmt = stmt.where(Appointment.appointment_at >= start)
    elif view != "all":
        if view == "week":
            target = today - timedelta(days=today.weekday())
            end_day = target + timedelta(days=7)
        elif view == "month":
            target = today.replace(day=1)
            end_day = (target + timedelta(days=32)).replace(day=1)
        else:
            target = today
            end_day = today + timedelta(days=1)
        stmt = stmt.where(Appointment.appointment_at >= datetime.combine(target, time.min), Appointment.appointment_at < datetime.combine(end_day, time.min))
    if date_to:
        stmt = stmt.where(Appointment.appointment_at < datetime.combine(date_to + timedelta(days=1), time.min))
    if doctor_id and user.role == Role.nurse:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if status:
        stmt = stmt.where(Appointment.status == status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Appointment.token_number.like(like),
                Patient.patient_code.like(like),
                Patient.name.like(like),
                User.full_name.like(like),
            )
        )
    appointments = db.scalars(stmt.order_by(Appointment.appointment_at.asc()).limit(250)).all()
    return [appointment_to_read(item) for item in appointments]


@router.get("/summary", response_model=AppointmentSummary)
def appointment_summary(db: Session = Depends(get_db), user: User = Depends(require_role(Role.doctor, Role.nurse))):
    start, end = day_bounds(date.today())
    clauses = [Appointment.appointment_at >= start, Appointment.appointment_at < end]
    if user.role == Role.doctor:
        clauses.append(Appointment.doctor_id == user.id)
    base = and_(*clauses)
    return AppointmentSummary(
        todays_appointments=db.scalar(select(func.count(Appointment.id)).where(base)) or 0,
        waiting_patients=db.scalar(select(func.count(Appointment.id)).where(base, Appointment.status == AppointmentStatus.waiting)) or 0,
        in_progress=db.scalar(select(func.count(Appointment.id)).where(base, Appointment.status == AppointmentStatus.in_progress)) or 0,
        completed_today=db.scalar(select(func.count(Appointment.id)).where(base, Appointment.status == AppointmentStatus.completed)) or 0,
        cancelled_today=db.scalar(select(func.count(Appointment.id)).where(base, Appointment.status == AppointmentStatus.cancelled)) or 0,
    )


@router.get("/notifications", response_model=list[AppointmentNotification])
def appointment_notifications(db: Session = Depends(get_db), user: User = Depends(require_role(Role.doctor, Role.nurse))):
    start, end = day_bounds(date.today())
    stmt = scoped_query(user).where(Appointment.appointment_at >= start, Appointment.appointment_at < end).order_by(Appointment.appointment_at.asc()).limit(8)
    notifications = []
    for appointment in db.scalars(stmt):
        label = appointment.token_number or f"#{appointment.id}"
        if appointment.status == AppointmentStatus.completed:
            message = f"{label} completed for {appointment.patient.name}"
        elif appointment.status == AppointmentStatus.cancelled:
            message = f"{label} cancelled for {appointment.patient.name}"
        elif appointment.appointment_at >= datetime.now():
            message = f"Upcoming {label} at {appointment.appointment_at:%I:%M %p}"
        else:
            message = f"{label} waiting for {appointment.patient.name}"
        notifications.append(AppointmentNotification(message=message, status=appointment.status, appointment_id=appointment.id, token_number=appointment.token_number))
    return notifications


@router.post("", response_model=AppointmentRead)
def book_appointment(payload: AppointmentCreate, db: Session = Depends(get_db), user: User = Depends(require_role(Role.nurse))):
    if not db.get(Patient, payload.patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    doctor = db.get(User, payload.doctor_id)
    if not doctor or doctor.role != Role.doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    appointment_at = datetime.combine(payload.appointment_date, payload.appointment_time)
    appointment = Appointment(
        token_number=next_token_number(db, payload.appointment_date),
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        booked_by_id=user.id,
        created_by=user.id,
        appointment_at=appointment_at,
        appointment_date=payload.appointment_date,
        appointment_time=payload.appointment_time,
        visit_type=payload.visit_type,
        priority=payload.priority,
        reason_for_visit=payload.reason_for_visit,
        reason=payload.reason_for_visit,
        notes=payload.notes,
        status=AppointmentStatus.waiting,
        follow_up_required=payload.follow_up_required,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment_to_read(appointment)


@router.patch("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.doctor, Role.nurse)),
):
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if user.role == Role.doctor and appointment.doctor_id != user.id:
        raise HTTPException(status_code=403, detail="Appointment is not assigned to this doctor")
    if user.role == Role.doctor and payload.status not in {AppointmentStatus.in_progress, AppointmentStatus.completed, None}:
        raise HTTPException(status_code=403, detail="Doctors can only start or complete assigned appointments")

    updates = payload.model_dump(exclude_unset=True)
    if "patient_id" in updates and not db.get(Patient, updates["patient_id"]):
        raise HTTPException(status_code=404, detail="Patient not found")
    if "doctor_id" in updates:
        doctor = db.get(User, updates["doctor_id"])
        if not doctor or doctor.role != Role.doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
    for key, value in updates.items():
        setattr(appointment, key, value)
        if key == "reason_for_visit":
            appointment.reason = value
    if "appointment_date" in updates or "appointment_time" in updates:
        appointment.appointment_at = datetime.combine(appointment.appointment_date, appointment.appointment_time)
    db.commit()
    db.refresh(appointment)
    return appointment_to_read(appointment)


@router.post("/{appointment_id}/start", response_model=AppointmentRead)
def start_consultation(appointment_id: int, db: Session = Depends(get_db), user: User = Depends(require_role(Role.doctor))):
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.doctor_id != user.id:
        raise HTTPException(status_code=403, detail="Appointment is not assigned to this doctor")
    appointment.status = AppointmentStatus.in_progress
    db.commit()
    db.refresh(appointment)
    return appointment_to_read(appointment)


@router.post("/{appointment_id}/complete", response_model=AppointmentRead)
def complete_consultation(
    appointment_id: int,
    payload: AppointmentComplete,
    db: Session = Depends(get_db),
    doctor: User = Depends(require_role(Role.doctor)),
):
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.doctor_id != doctor.id:
        raise HTTPException(status_code=403, detail="Appointment is not assigned to this doctor")
    visit = Visit(
        patient_id=appointment.patient_id,
        doctor_id=doctor.id,
        symptoms=payload.symptoms or appointment.reason_for_visit or "Consultation completed from appointment.",
        diagnosis=payload.diagnosis,
        doctor_notes=payload.doctor_notes,
        ai_summary=payload.ai_summary,
    )
    db.add(visit)
    db.flush()
    if payload.prescription:
        db.add(
            PrescriptionItem(
                visit_id=visit.id,
                medicine_name="Doctor prescription",
                dosage="As written",
                frequency="As written",
                duration="As written",
                instructions=payload.prescription,
                doctor_approved=True,
            )
        )
    appointment.status = AppointmentStatus.completed
    db.commit()
    db.refresh(appointment)
    return appointment_to_read(appointment)


@router.delete("/{appointment_id}")
def delete_appointment(appointment_id: int, db: Session = Depends(get_db), user: User = Depends(require_role(Role.doctor, Role.nurse))):
    appointment = db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if user.role == Role.doctor and appointment.doctor_id != user.id:
        raise HTTPException(status_code=403, detail="Appointment is not assigned to this doctor")
    db.delete(appointment)
    db.commit()
    return {"deleted": True}

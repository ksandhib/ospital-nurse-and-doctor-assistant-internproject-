from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Patient, PrescriptionItem, Role, User, Visit
from app.schemas import PrescriptionItemCreate, VisitCreate, VisitRead
from app.services.prescription_pdf import build_prescription_pdf


router = APIRouter()


@router.post("", response_model=VisitRead)
def create_visit(payload: VisitCreate, db: Session = Depends(get_db), doctor: User = Depends(require_role(Role.doctor))):
    if not db.get(Patient, payload.patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    visit = Visit(**payload.model_dump(), doctor_id=doctor.id)
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


@router.post("/{visit_id}/prescriptions")
def add_prescription_items(
    visit_id: int,
    items: list[PrescriptionItemCreate],
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.doctor)),
):
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    created = []
    for payload in items:
        item = PrescriptionItem(visit_id=visit_id, **payload.model_dump())
        db.add(item)
        created.append(item)
    db.commit()
    return {"created": len(created), "doctor_approved_required": True}


@router.get("/{visit_id}/prescription.pdf")
def prescription_pdf(visit_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor))):
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    return build_prescription_pdf(visit)


@router.get("/patient/{patient_id}", response_model=list[VisitRead])
def visits_for_patient(patient_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor, Role.nurse))):
    return list(db.scalars(select(Visit).where(Visit.patient_id == patient_id).order_by(Visit.created_at.desc())))

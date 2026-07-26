from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import get_db
from app.dependencies import require_role
from app.models import Patient, PatientDocument, Role, User, Vital
from app.schemas import PatientCreate, PatientRead, PatientUpdate, VitalCreate, VitalRead
from app.utils.patient_codes import calculate_bmi, next_patient_code


router = APIRouter()


@router.get("", response_model=list[PatientRead])
def search_patients(q: str | None = None, db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor, Role.nurse))):
    stmt = select(Patient).order_by(Patient.created_at.desc()).limit(100)
    if q:
        like = f"%{q}%"
        stmt = select(Patient).where(
            or_(
                Patient.patient_code.like(like),
                Patient.name.like(like),
                Patient.phone.like(like),
                Patient.chronic_diseases.like(like),
            )
        ).order_by(Patient.created_at.desc())
    return list(db.scalars(stmt))


@router.post("", response_model=PatientRead)
def register_patient(payload: PatientCreate, db: Session = Depends(get_db), _: User = Depends(require_role(Role.nurse))):
    patient = Patient(**payload.model_dump(), patient_code=next_patient_code(db))
    patient.bmi = calculate_bmi(patient.height_cm, patient.weight_kg)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(patient_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor, Role.nurse))):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.patch("/{patient_id}", response_model=PatientRead)
def update_patient(patient_id: int, payload: PatientUpdate, db: Session = Depends(get_db), _: User = Depends(require_role(Role.nurse))):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, key, value)
    patient.bmi = calculate_bmi(patient.height_cm, patient.weight_kg)
    db.commit()
    db.refresh(patient)
    return patient


@router.post("/{patient_id}/vitals", response_model=VitalRead)
def record_vitals(
    patient_id: int,
    payload: VitalCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.nurse)),
):
    if patient_id != payload.patient_id:
        raise HTTPException(status_code=400, detail="Patient ID mismatch")
    if not db.get(Patient, patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    vital = Vital(**payload.model_dump(), recorded_by_id=user.id)
    db.add(vital)
    db.commit()
    db.refresh(vital)
    return vital


@router.get("/{patient_id}/timeline")
def patient_timeline(patient_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor, Role.nurse))):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "patient": {"id": patient.id, "patient_code": patient.patient_code, "name": patient.name},
        "vitals": sorted([{"type": "vital", "at": v.recorded_at, "data": VitalRead.model_validate(v).model_dump()} for v in patient.vitals], key=lambda x: x["at"], reverse=True),
        "visits": [
            {
                "type": "visit",
                "at": visit.created_at,
                "symptoms": visit.symptoms,
                "diagnosis": visit.diagnosis,
                "prescription": [
                    {
                        "medicine_name": item.medicine_name,
                        "dosage": item.dosage,
                        "frequency": item.frequency,
                        "duration": item.duration,
                        "doctor_approved": item.doctor_approved,
                    }
                    for item in visit.prescription_items
                ],
            }
            for visit in sorted(patient.visits, key=lambda item: item.created_at, reverse=True)
        ],
        "documents": [
            {"type": doc.document_type, "at": doc.uploaded_at, "title": doc.title, "file_path": doc.file_path}
            for doc in sorted(patient.documents, key=lambda item: item.uploaded_at, reverse=True)
        ],
    }


@router.post("/{patient_id}/documents")
async def upload_document(
    patient_id: int,
    document_type: str,
    title: str,
    file: UploadFile = File(...),
    notes: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(Role.nurse)),
):
    if not db.get(Patient, patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    settings = get_settings()
    upload_dir = Path(settings.upload_dir) / "documents" / str(patient_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix
    destination = upload_dir / f"{uuid4().hex}{suffix}"
    destination.write_bytes(await file.read())
    doc = PatientDocument(
        patient_id=patient_id,
        uploaded_by_id=user.id,
        document_type=document_type,
        title=title,
        file_path=str(destination),
        notes=notes,
    )
    db.add(doc)
    db.commit()
    return {"id": doc.id, "file_path": doc.file_path}

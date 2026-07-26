from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Patient, Role, User
from app.schemas import AiMedicineRecommendationResponse, AiMedicineRequest, AiResponse, AiSymptomRequest
from app.services.ai_service import AiClinicalService


router = APIRouter()
service = AiClinicalService()


@router.post("/symptom-analysis", response_model=AiResponse)
def symptom_analysis(payload: AiSymptomRequest, db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor))):
    patient = db.get(Patient, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return AiResponse(content=service.symptom_analysis(db, patient, payload.symptoms, payload.vitals))


@router.post("/medicine-recommendations", response_model=AiMedicineRecommendationResponse)
def medicine_recommendations(payload: AiMedicineRequest, db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor))):
    patient = db.get(Patient, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    content, recommendations = service.medicine_recommendations(db, patient, payload.symptoms)
    return AiMedicineRecommendationResponse(
        content=content,
        patient_id=patient.id,
        current_symptoms=payload.symptoms,
        recommendations=recommendations,
    )


@router.get("/patient-summary/{patient_id}", response_model=AiResponse)
def patient_summary(patient_id: int, db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor))):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return AiResponse(content=service.patient_summary(db, patient))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Patient


def next_patient_code(db: Session) -> str:
    last_id = db.scalar(select(Patient.id).order_by(Patient.id.desc()).limit(1)) or 0
    return f"PT{last_id + 1:06d}"


def calculate_bmi(height_cm: float | None, weight_kg: float | None) -> float | None:
    if not height_cm or not weight_kg:
        return None
    height_m = height_cm / 100
    if height_m <= 0:
        return None
    return round(weight_kg / (height_m * height_m), 2)

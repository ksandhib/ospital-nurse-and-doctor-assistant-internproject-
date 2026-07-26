from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models import Medicine, Role, User


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "doctor@clinicos.example").first():
            db.add(
                User(
                    full_name="Dr. Asha Raman",
                    email="doctor@clinicos.example",
                    password_hash=hash_password("Doctor@123"),
                    role=Role.doctor,
                    specialty="Internal Medicine",
                )
            )
        if not db.query(User).filter(User.email == "nurse@clinicos.example").first():
            db.add(
                User(
                    full_name="Nurse Meera Das",
                    email="nurse@clinicos.example",
                    password_hash=hash_password("Nurse@123"),
                    role=Role.nurse,
                )
            )
        if not db.query(Medicine).filter(Medicine.medicine_code == "MED0001").first():
            db.add(
                Medicine(
                    medicine_code="MED0001",
                    medicine_name="Paracetamol 500 mg",
                    generic_name="Acetaminophen",
                    brand_name="ClinicCare",
                    drug_class="Analgesic/Antipyretic",
                    therapeutic_category="Fever and pain",
                    indications="Fever, mild pain, headache, body pain",
                    symptoms_keywords="Fever, Body Pain, Headache",
                    search_keywords="Fever, Pain, Temperature, Body ache",
                    medicine_description="Used to reduce fever and relieve mild to moderate pain.",
                    clinical_notes="Review liver disease history and total daily acetaminophen exposure.",
                    common_diseases="Viral fever, influenza-like illness, mild headache",
                    alternative_medicines="Paracetamol 500 mg",
                    dosage_form="Tablet",
                    strength="500 mg",
                    adult_dose="As directed by physician; respect local maximum daily dose guidance.",
                    contraindications="Severe liver disease, known hypersensitivity",
                    side_effects="Nausea, rash, rare liver toxicity",
                    drug_interactions="Alcohol, warfarin caution",
                    pregnancy_safety="Use only under physician guidance",
                    stock_quantity=120,
                )
            )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()

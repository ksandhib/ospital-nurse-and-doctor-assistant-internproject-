from pathlib import Path

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models import Medicine


EXPECTED_COLUMNS = {
    "Medicine ID": "medicine_code",
    "Medicine Name": "medicine_name",
    "Generic Name": "generic_name",
    "Brand Name": "brand_name",
    "Drug Class": "drug_class",
    "Therapeutic Category": "therapeutic_category",
    "Indications": "indications",
    "Dosage Form": "dosage_form",
    "Strength": "strength",
    "Adult Dose": "adult_dose",
    "Pediatric Dose": "pediatric_dose",
    "Elderly Dose": "elderly_dose",
    "Contraindications": "contraindications",
    "Side Effects": "side_effects",
    "Drug Interactions": "drug_interactions",
    "Pregnancy Safety": "pregnancy_safety",
    "Storage Conditions": "storage_conditions",
    "Manufacturer": "manufacturer",
    "Prescription Required": "prescription_required",
    "Notes": "notes",
    "Symptoms Keywords": "symptoms_keywords",
    "Search Keywords": "search_keywords",
    "Medicine Description": "medicine_description",
    "Clinical Notes": "clinical_notes",
    "Common Diseases": "common_diseases",
    "Alternative Medicines": "alternative_medicines",
}


def import_medicines_from_excel(path: Path, db: Session) -> dict[str, int | list[str]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    headers = [str(cell.value).strip() if cell.value is not None else "" for cell in next(sheet.iter_rows(max_row=1))]
    missing = [name for name in EXPECTED_COLUMNS if name not in headers]
    if missing:
        return {"created": 0, "updated": 0, "errors": [f"Missing columns: {', '.join(missing)}"]}

    index = {header: headers.index(header) for header in EXPECTED_COLUMNS}
    created = 0
    updated = 0
    errors: list[str] = []

    for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        values = {EXPECTED_COLUMNS[column]: row[idx] for column, idx in index.items()}
        code = str(values.get("medicine_code") or "").strip()
        name = str(values.get("medicine_name") or "").strip()
        if not code or not name:
            errors.append(f"Row {row_number}: Medicine ID and Medicine Name are required")
            continue
        values["medicine_code"] = code
        values["medicine_name"] = name
        values["prescription_required"] = str(values.get("prescription_required", "true")).strip().lower() in {"1", "yes", "true", "required"}
        medicine = db.query(Medicine).filter(Medicine.medicine_code == code).one_or_none()
        if medicine:
            for key, value in values.items():
                setattr(medicine, key, value)
            updated += 1
        else:
            db.add(Medicine(**values))
            created += 1
    db.commit()
    return {"created": created, "updated": updated, "errors": errors}

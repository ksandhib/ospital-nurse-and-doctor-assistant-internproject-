from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database import get_db
from app.dependencies import require_role
from app.models import Medicine, Role, User
from app.schemas import MedicineRead
from app.services.medicine_importer import import_medicines_from_excel


router = APIRouter()


@router.get("", response_model=list[MedicineRead])
def search_medicines(q: str | None = None, db: Session = Depends(get_db), _: User = Depends(require_role(Role.doctor, Role.nurse))):
    stmt = select(Medicine).order_by(Medicine.medicine_name).limit(100)
    if q:
        like = f"%{q}%"
        stmt = (
            select(Medicine)
            .where(
                or_(
                    Medicine.medicine_name.like(like),
                    Medicine.generic_name.like(like),
                    Medicine.brand_name.like(like),
                    Medicine.indications.like(like),
                    Medicine.therapeutic_category.like(like),
                )
            )
            .order_by(Medicine.medicine_name)
        )
    return list(db.scalars(stmt))


@router.post("/import")
async def import_medicines(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_role(Role.nurse)),
):
    settings = get_settings()
    upload_dir = Path(settings.upload_dir) / "medicine-imports"
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / f"{uuid4().hex}-{file.filename}"
    destination.write_bytes(await file.read())
    return import_medicines_from_excel(destination, db)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.database import Base, engine
from app.routers import ai, appointments, auth, chat, dashboard, medicines, patients, reports, visits
from app.services.appointment_schema import ensure_appointment_schema
from app.services.chat_schema import ensure_chat_schema


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
app.include_router(visits.router, prefix="/api/visits", tags=["EMR Visits"])
app.include_router(medicines.router, prefix="/api/medicines", tags=["Medicines"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Clinical Support"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["Appointments"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI Chat Assistant"])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.on_event("startup")
def startup() -> None:
    # Safe on every startup: create_all only creates tables that don't exist
    # yet (checkfirst=True is the default), so an already-migrated production
    # MySQL database is left untouched. This just guarantees a completely
    # fresh database (SQLite for local dev, or a brand-new MySQL schema)
    # always has every table before the app accepts traffic - previously only
    # appointments/chat tables were guaranteed here, so a cold start without
    # running `python -m app.seed` first would 500 on login/patients/medicines
    # with "no such table" (or fail outright on MySQL's FK checks).
    Base.metadata.create_all(bind=engine)
    ensure_appointment_schema()
    ensure_chat_schema()

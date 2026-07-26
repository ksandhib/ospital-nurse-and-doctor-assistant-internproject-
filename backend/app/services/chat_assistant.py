import json
import re
from datetime import date, datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Appointment, AppointmentStatus, Medicine, Patient, PrescriptionItem, Role, User, Visit
from app.services.ollama_client import OllamaClient, OllamaUnavailableError


DATA_SOURCE_DATABASE = "AI ClinicOS Database"
DATA_SOURCE_OLLAMA = "Ollama"
DATA_SOURCE_BOTH = "AI ClinicOS Database + Ollama"
CLINICAL_SAFETY_FOOTER = (
    "\n\n**AI-generated information is intended to assist healthcare professionals and should not replace clinical "
    "judgment. The doctor is responsible for all final medical decisions.**"
)


class ChatAssistantService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = OllamaClient()

    def answer(self, db: Session, user: User, question: str) -> tuple[str, str]:
        normalized = question.lower().strip()
        if user.role == Role.nurse and self._looks_clinical(normalized):
            return (
                "I can help with registrations, patients, appointments, medicines, and reports. "
                "Clinical diagnosis, prescription recommendations, and consultation decision support are available to doctors only.",
                DATA_SOURCE_DATABASE,
            )

        db_answer = self._database_answer(db, user, question, normalized)
        if db_answer:
            return db_answer

        if self._looks_clinical(normalized):
            return self._clinical_answer(question)

        context = self._general_context(db, user, question)
        if self.client.is_configured():
            prompt = f"""
You are AI ClinicOS Assistant. Answer the staff member's question using the supplied clinic context first.
If the context is insufficient, say what data is missing and keep the answer professional and concise.

User role: {user.role.value}
Question: {question}
Relevant clinic context JSON:
{json.dumps(context, default=str)}
"""
            try:
                content = self.client.chat(
                    "You answer questions for a clinic EMR using only relevant supplied context unless clearly asked for general knowledge.",
                    prompt,
                )
                return content, DATA_SOURCE_BOTH if context else DATA_SOURCE_OLLAMA
            except OllamaUnavailableError:
                pass

        if context:
            return self._context_summary(context), DATA_SOURCE_DATABASE
        return (
            "I could not find matching clinic data for that question. Try asking about a patient ID, today's appointments, medicines, follow-ups, or report totals.",
            DATA_SOURCE_DATABASE,
        )

    def _looks_clinical(self, normalized: str) -> bool:
        clinical_terms = [
            "diagnosis",
            "differential",
            "prescribe",
            "prescription",
            "medicine commonly used",
            "antibiotic",
            "treatment",
            "symptoms of",
            "explain hypertension",
            "explain dengue",
            "chest pain",
            "viral fever",
            "sinusitis",
        ]
        return any(term in normalized for term in clinical_terms)

    def _clinical_answer(self, question: str) -> tuple[str, str]:
        if not self.client.is_configured():
            return (
                "Ollama is not configured, so doctor-only clinical knowledge answers are currently unavailable. "
                "Set OLLAMA_BASE_URL and OLLAMA_MODEL in backend/.env to enable this assistant path." + CLINICAL_SAFETY_FOOTER,
                DATA_SOURCE_OLLAMA,
            )
        try:
            content = self.client.chat(
                "You are AI ClinicOS, a cautious doctor-only clinical assistant. Provide concise medical education, "
                "red flags, and a clear reminder that final decisions require doctor judgment.",
                question,
            )
        except OllamaUnavailableError:
            return (
                f"Could not reach Ollama at {self.client.base_url} (model '{self.client.model}'). Start Ollama and "
                f"make sure the model is pulled (`ollama pull {self.client.model}`), then try again."
                + CLINICAL_SAFETY_FOOTER,
                DATA_SOURCE_OLLAMA,
            )
        return content + CLINICAL_SAFETY_FOOTER, DATA_SOURCE_OLLAMA

    def _database_answer(self, db: Session, user: User, question: str, normalized: str) -> tuple[str, str] | None:
        today = date.today()
        tomorrow = today + timedelta(days=1)

        patient_code = re.search(r"\bpt\d{3,}\b", normalized)
        if patient_code and ("history" in normalized or "show" in normalized or "patient" in normalized):
            patient = db.scalar(select(Patient).where(func.lower(Patient.patient_code) == patient_code.group(0)))
            if not patient:
                return f"No patient found with ID `{patient_code.group(0).upper()}`.", DATA_SOURCE_DATABASE
            return self._patient_history(db, patient, user), DATA_SOURCE_DATABASE

        if "registered today" in normalized or "today's new patients" in normalized or "todays new patients" in normalized:
            start, end = self._date_window(today)
            rows = db.scalars(select(Patient).where(and_(Patient.created_at >= start, Patient.created_at < end)).order_by(Patient.created_at.desc())).all()
            return self._patient_list(f"{len(rows)} patients were registered today.", rows), DATA_SOURCE_DATABASE

        if "above 60" in normalized or "over 60" in normalized:
            rows = db.scalars(select(Patient).where(Patient.age > 60).order_by(Patient.age.desc()).limit(25)).all()
            return self._patient_list(f"{len(rows)} patients above 60 are shown below.", rows), DATA_SOURCE_DATABASE

        disease = self._disease_term(normalized)
        if disease:
            like = f"%{disease}%"
            rows = db.scalars(
                select(Patient)
                .where(or_(func.lower(Patient.chronic_diseases).like(like), func.lower(Patient.notes).like(like)))
                .order_by(Patient.created_at.desc())
                .limit(25)
            ).all()
            return self._patient_list(f"Patients matching `{disease}` in chronic diseases or notes:", rows), DATA_SOURCE_DATABASE

        if "follow-up" in normalized or "follow up" in normalized:
            rows = db.scalars(select(Visit).where(Visit.follow_up_date.is_not(None), Visit.follow_up_date <= today).order_by(Visit.follow_up_date.asc()).limit(25)).all()
            lines = [f"- `{visit.patient.patient_code}` {visit.patient.name}: follow-up due {visit.follow_up_date}" for visit in rows]
            return ("Pending or missed follow-ups:\n" + ("\n".join(lines) if lines else "No pending follow-ups found.")), DATA_SOURCE_DATABASE

        if "appointment" in normalized:
            if "most appointments" in normalized:
                rows = db.execute(
                    select(User.full_name, func.count(Appointment.id).label("total"))
                    .join(Appointment, Appointment.doctor_id == User.id)
                    .group_by(User.id, User.full_name)
                    .order_by(func.count(Appointment.id).desc())
                    .limit(10)
                ).all()
                return self._table("Doctors by appointment volume", ["Doctor", "Appointments"], rows), DATA_SOURCE_DATABASE
            appointment_date = tomorrow if "tomorrow" in normalized else today if "today" in normalized else None
            status = next((item.value for item in AppointmentStatus if item.value.replace("_", " ") in normalized), None)
            return self._appointment_answer(db, appointment_date, status), DATA_SOURCE_DATABASE

        if "medicine" in normalized or self._medicine_query(normalized):
            return self._medicine_answer(db, normalized)

        if "total patients" in normalized:
            total = db.scalar(select(func.count(Patient.id))) or 0
            return f"Total patients: **{total}**", DATA_SOURCE_DATABASE

        if "monthly appointments" in normalized:
            rows = db.execute(
                select(func.strftime("%Y-%m", Appointment.appointment_at), func.count(Appointment.id))
                .group_by(func.strftime("%Y-%m", Appointment.appointment_at))
                .order_by(func.strftime("%Y-%m", Appointment.appointment_at).desc())
                .limit(12)
            ).all()
            return self._table("Monthly appointments", ["Month", "Appointments"], rows), DATA_SOURCE_DATABASE

        if "most prescribed" in normalized:
            rows = db.execute(
                select(PrescriptionItem.medicine_name, func.count(PrescriptionItem.id).label("total"))
                .group_by(PrescriptionItem.medicine_name)
                .order_by(func.count(PrescriptionItem.id).desc())
                .limit(10)
            ).all()
            return self._table("Most prescribed medicines", ["Medicine", "Prescriptions"], rows), DATA_SOURCE_DATABASE

        if "average consultations today" in normalized:
            start, end = self._date_window(today)
            count = db.scalar(select(func.count(Visit.id)).where(and_(Visit.created_at >= start, Visit.created_at < end))) or 0
            doctors = db.scalar(select(func.count(User.id)).where(User.role == Role.doctor, User.is_active.is_(True))) or 1
            return f"Average consultations today: **{count / max(doctors, 1):.1f} per active doctor** ({count} total consultations).", DATA_SOURCE_DATABASE

        return None

    def _patient_history(self, db: Session, patient: Patient, user: User) -> str:
        visit_stmt = select(Visit).where(Visit.patient_id == patient.id).order_by(Visit.created_at.desc()).limit(8)
        if user.role == Role.doctor:
            visit_stmt = visit_stmt.where(Visit.doctor_id == user.id)
        visits = db.scalars(visit_stmt).all()
        appointments = db.scalars(select(Appointment).where(Appointment.patient_id == patient.id).order_by(Appointment.appointment_at.desc()).limit(5)).all()
        lines = [
            f"### {patient.patient_code} - {patient.name}",
            f"- Age/Gender: {patient.age or '-'} / {patient.gender or '-'}",
            f"- Phone: {patient.phone}",
            f"- Chronic diseases: {patient.chronic_diseases or 'Not recorded'}",
            f"- Allergies: {patient.allergies or 'Not recorded'}",
            "",
            "### Recent visits",
        ]
        if visits:
            lines.extend(f"- {visit.created_at:%Y-%m-%d}: {visit.symptoms} | Diagnosis: {visit.diagnosis or 'Pending'}" for visit in visits)
        else:
            lines.append("- No visits available for your role.")
        lines.append("\n### Recent appointments")
        lines.extend(
            [f"- {appt.appointment_at:%Y-%m-%d %H:%M}: {appt.status.value} with {appt.doctor.full_name if appt.doctor else 'Unassigned'}" for appt in appointments]
            or ["- No appointments found."]
        )
        return "\n".join(lines)

    def _appointment_answer(self, db: Session, appointment_date: date | None, status: str | None) -> str:
        stmt = select(Appointment).order_by(Appointment.appointment_at.asc()).limit(50)
        label = "Appointments"
        if appointment_date:
            start, end = self._date_window(appointment_date)
            stmt = stmt.where(and_(Appointment.appointment_at >= start, Appointment.appointment_at < end))
            label = f"Appointments on {appointment_date.isoformat()}"
        if status:
            stmt = stmt.where(Appointment.status == AppointmentStatus(status))
            label += f" with status {status.replace('_', ' ')}"
        rows = db.scalars(stmt).all()
        lines = [
            f"{label}: **{len(rows)}**",
            "",
            "| Token | Patient | Doctor | Time | Status |",
            "| --- | --- | --- | --- | --- |",
        ]
        lines.extend(
            f"| {appt.token_number or '-'} | {appt.patient.patient_code} - {appt.patient.name} | {appt.doctor.full_name if appt.doctor else '-'} | {appt.appointment_at:%Y-%m-%d %H:%M} | {appt.status.value} |"
            for appt in rows[:25]
        )
        if not rows:
            lines.append("| - | No appointments found | - | - | - |")
        return "\n".join(lines)

    def _medicine_answer(self, db: Session, normalized: str) -> tuple[str, str]:
        if "how many medicines" in normalized or "total medicines" in normalized:
            total = db.scalar(select(func.count(Medicine.id))) or 0
            return f"Total medicines in the database: **{total}**", DATA_SOURCE_DATABASE
        if "low stock" in normalized:
            rows = db.scalars(select(Medicine).where(Medicine.stock_quantity <= 10).order_by(Medicine.stock_quantity.asc()).limit(25)).all()
            lines = [f"- {med.medicine_name}: {med.stock_quantity} in stock" for med in rows]
            return "Low-stock medicines:\n" + ("\n".join(lines) if lines else "No low-stock medicines found using threshold <= 10."), DATA_SOURCE_DATABASE
        term = self._extract_search_term(normalized)
        like = f"%{term}%"
        rows = db.scalars(
            select(Medicine)
            .where(
                or_(
                    func.lower(Medicine.medicine_name).like(like),
                    func.lower(Medicine.generic_name).like(like),
                    func.lower(Medicine.brand_name).like(like),
                    func.lower(Medicine.indications).like(like),
                    func.lower(Medicine.common_diseases).like(like),
                    func.lower(Medicine.symptoms_keywords).like(like),
                    func.lower(Medicine.search_keywords).like(like),
                )
            )
            .limit(10)
        ).all()
        lines = [
            "| Medicine | Generic | Use/Indication | Stock |",
            "| --- | --- | --- | --- |",
        ]
        lines.extend(f"| {med.medicine_name} | {med.generic_name or '-'} | {(med.indications or med.common_diseases or '-')[:140]} | {med.stock_quantity} |" for med in rows)
        if not rows:
            lines.append("| - | - | No matching medicines found. | - |")
        return f"Medicine search for `{term}`:\n\n" + "\n".join(lines), DATA_SOURCE_DATABASE

    def _general_context(self, db: Session, user: User, question: str) -> dict:
        term = self._extract_search_term(question.lower())
        patients = db.scalars(
            select(Patient)
            .where(or_(func.lower(Patient.patient_code).like(f"%{term}%"), func.lower(Patient.name).like(f"%{term}%"), func.lower(Patient.chronic_diseases).like(f"%{term}%")))
            .limit(5)
        ).all()
        medicines = db.scalars(select(Medicine).where(func.lower(Medicine.medicine_name).like(f"%{term}%")).limit(5)).all()
        return {
            "role": user.role.value,
            "matched_patients": [{"code": p.patient_code, "name": p.name, "age": p.age, "chronic_diseases": p.chronic_diseases} for p in patients],
            "matched_medicines": [{"name": m.medicine_name, "generic": m.generic_name, "indications": m.indications} for m in medicines],
        }

    def _context_summary(self, context: dict) -> str:
        lines = ["I found these relevant clinic records:"]
        for patient in context.get("matched_patients", []):
            lines.append(f"- Patient `{patient['code']}` {patient['name']}: age {patient['age'] or '-'}, chronic diseases: {patient['chronic_diseases'] or 'Not recorded'}")
        for medicine in context.get("matched_medicines", []):
            lines.append(f"- Medicine {medicine['name']}: {medicine['generic'] or '-'}; {medicine['indications'] or 'No indication recorded'}")
        return "\n".join(lines) if len(lines) > 1 else "No matching clinic records found."

    def _patient_list(self, heading: str, rows: list[Patient]) -> str:
        lines = [heading, "", "| Patient ID | Name | Age | Phone | Chronic diseases |", "| --- | --- | --- | --- | --- |"]
        lines.extend(f"| {p.patient_code} | {p.name} | {p.age or '-'} | {p.phone} | {p.chronic_diseases or '-'} |" for p in rows[:25])
        if not rows:
            lines.append("| - | No patients found | - | - | - |")
        return "\n".join(lines)

    def _table(self, title: str, headers: list[str], rows: list[tuple]) -> str:
        lines = [f"### {title}", "", "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
        if not rows:
            lines.append("| " + " | ".join(["-" for _ in headers]) + " |")
        return "\n".join(lines)

    def _date_window(self, value: date) -> tuple[datetime, datetime]:
        start = datetime.combine(value, datetime.min.time())
        return start, start + timedelta(days=1)

    def _disease_term(self, normalized: str) -> str | None:
        for disease in ["diabetes", "diabetic", "hypertension", "asthma", "fever"]:
            if disease in normalized:
                return "diabetes" if disease == "diabetic" else disease
        return None

    def _medicine_query(self, normalized: str) -> bool:
        return normalized.startswith("search ") or normalized.startswith("explain ")

    def _extract_search_term(self, normalized: str) -> str:
        cleaned = re.sub(r"^(search|explain|show|list|find)\s+", "", normalized).strip()
        cleaned = cleaned.replace("medicines for", "").replace("medicine for", "").replace("medicine", "").strip()
        return cleaned.split("?")[0].strip() or normalized.strip()

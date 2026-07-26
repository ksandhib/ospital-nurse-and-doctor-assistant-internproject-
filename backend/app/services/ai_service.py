import json
import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Medicine, Patient, Visit
from app.schemas import MedicineRecommendation
from app.services.ollama_client import OllamaClient, OllamaUnavailableError


SYSTEM_PROMPT = """You are AI ClinicOS, a cautious clinical decision-support assistant.
You support licensed doctors only. Do not claim certainty. Do not prescribe automatically.
Always include warnings, red flags, and a reminder that the doctor must approve final decisions.
Use concise headings and clinically relevant reasoning."""

STOPWORDS = {
    "and",
    "with",
    "for",
    "the",
    "has",
    "have",
    "having",
    "from",
    "days",
    "day",
    "high",
    "low",
    "mild",
    "moderate",
    "severe",
    "patient",
    "complains",
    "complaining",
}


class AiClinicalService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = OllamaClient()

    def _complete(self, user_prompt: str) -> str:
        try:
            return self.client.chat(SYSTEM_PROMPT, user_prompt)
        except OllamaUnavailableError:
            return (
                f"Could not reach Ollama at {self.client.base_url} (model '{self.client.model}'). "
                "Start Ollama and run `ollama pull "
                f"{self.client.model}` if you have not already, then try again. "
                "Set OLLAMA_BASE_URL / OLLAMA_MODEL in backend/.env if Ollama runs elsewhere."
            )

    def _complete_json(self, user_prompt: str) -> dict:
        return self.client.chat_json(SYSTEM_PROMPT, user_prompt)

    def patient_context(self, db: Session, patient: Patient) -> dict:
        visits = db.scalars(select(Visit).where(Visit.patient_id == patient.id).order_by(Visit.created_at.desc())).all()
        return {
            "patient_code": patient.patient_code,
            "age": patient.age,
            "gender": patient.gender,
            "blood_group": patient.blood_group,
            "allergies": patient.allergies,
            "chronic_diseases": patient.chronic_diseases,
            "previous_visits": [
                {
                    "symptoms": visit.symptoms,
                    "diagnosis": visit.diagnosis,
                    "notes": visit.doctor_notes,
                    "visit_date": visit.created_at,
                    "prescriptions": [
                        {
                            "medicine_name": item.medicine_name,
                            "dosage": item.dosage,
                            "frequency": item.frequency,
                            "duration": item.duration,
                        }
                        for item in visit.prescription_items
                    ],
                }
                for visit in visits
            ],
        }

    def symptom_analysis(self, db: Session, patient: Patient, symptoms: str, vitals: str | None) -> str:
        context = self.patient_context(db, patient)
        prompt = f"""
Analyze the symptoms for doctor review.

Patient context JSON:
{json.dumps(context, default=str)}

Current symptoms:
{symptoms}

Current vitals:
{vitals or "Not supplied"}

Return sections:
Possible Conditions, Differential Diagnoses, Suggested Investigations, Medicine Categories,
General Treatment Considerations, Warnings and Red Flags, Confidence Explanation.
"""
        return self._complete(prompt)

    def patient_summary(self, db: Session, patient: Patient) -> str:
        context = self.patient_context(db, patient)
        prompt = f"""
Summarize this patient's medical history for a doctor opening the profile.
Include chronic diseases, recent diagnoses, current medicines if inferable, allergies,
recent lab findings if present, missed follow-ups if inferable, and important notes.

Patient context JSON:
{json.dumps(context, default=str)}
"""
        return self._complete(prompt)

    # Common multi-word symptom phrases. Checked as exact phrases first so
    # "chest pain" is matched as one clinical concept, not scored only as the
    # two loose words "chest" and "pain" - this keeps results precise for the
    # exact symptoms entered rather than approximate/loose word overlap.
    KNOWN_PHRASES = [
        "chest pain", "shortness of breath", "sore throat", "high fever",
        "low grade fever", "loose motion", "loose motions", "abdominal pain",
        "stomach pain", "back pain", "joint pain", "muscle pain", "body pain",
        "body ache", "body aches", "runny nose", "blocked nose", "difficulty breathing",
        "skin rash", "urinary tract infection", "burning urination",
        "loss of appetite", "weight loss", "night sweats", "blurred vision",
        "dry cough", "wet cough", "productive cough",
    ]

    def _symptom_terms(self, symptoms: str) -> list[str]:
        lowered = symptoms.lower()
        terms: list[str] = []
        for phrase in self.KNOWN_PHRASES:
            if phrase in lowered and phrase not in terms:
                terms.append(phrase)
        comma_terms = [part.strip().lower() for part in symptoms.split(",") if len(part.strip()) > 2]
        parts = re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", lowered)
        for term in comma_terms:
            if term not in STOPWORDS and term not in terms:
                terms.append(term)
        for part in parts:
            term = part.strip("-")
            if term and term not in STOPWORDS and term not in terms:
                terms.append(term)
        return terms[:16]

    def _medicine_search(self, db: Session, symptoms: str) -> list[tuple[Medicine, int, list[str]]]:
        terms = self._symptom_terms(symptoms)
        stmt = select(Medicine).limit(20)
        if terms:
            clauses = []
            for term in terms:
                like = f"%{term}%"
                lowered_like = like.lower()
                clauses.extend(
                    [
                        func.lower(Medicine.symptoms_keywords).like(lowered_like),
                        func.lower(Medicine.search_keywords).like(lowered_like),
                        func.lower(Medicine.medicine_description).like(lowered_like),
                        func.lower(Medicine.common_diseases).like(lowered_like),
                        func.lower(Medicine.indications).like(lowered_like),
                        func.lower(Medicine.therapeutic_category).like(lowered_like),
                        func.lower(Medicine.medicine_name).like(lowered_like),
                        func.lower(Medicine.generic_name).like(lowered_like),
                    ]
                )
            stmt = select(Medicine).where(or_(*clauses)).limit(50)
        medicines = db.scalars(stmt).all()
        ranked: list[tuple[Medicine, int, list[str]]] = []
        weighted_fields = [
            ("symptoms_keywords", 5),
            ("search_keywords", 4),
            ("medicine_description", 3),
            ("common_diseases", 3),
            ("indications", 2),
            ("clinical_notes", 2),
            ("therapeutic_category", 1),
            ("medicine_name", 1),
            ("generic_name", 1),
        ]
        for med in medicines:
            score = 0
            matched: list[str] = []
            for term in terms:
                # Multi-word phrases ("chest pain") are more clinically specific than a
                # single loose word ("pain"), so they carry more weight toward an exact match.
                phrase_bonus = 2 if " " in term else 1
                for field_name, weight in weighted_fields:
                    value = (getattr(med, field_name) or "").lower()
                    if term in value:
                        score += weight * phrase_bonus
                        if term.title() not in matched:
                            matched.append(term.title())
                    if value and term == value:
                        score += weight
                if term == (med.medicine_name or "").lower() or term == (med.generic_name or "").lower():
                    score += 4
            if score > 0 or not terms:
                ranked.append((med, score, matched))
        return sorted(ranked, key=lambda item: item[1], reverse=True)[:10]

    def _warnings_for(self, patient: Patient, medicine: Medicine) -> list[str]:
        warnings: list[str] = []
        allergy_text = (patient.allergies or "").lower()
        combined = " ".join(
            filter(
                None,
                [
                    medicine.medicine_name,
                    medicine.generic_name,
                    medicine.contraindications,
                    medicine.side_effects,
                    medicine.drug_interactions,
                ],
            )
        ).lower()
        if allergy_text and any(part.strip() and part.strip() in combined for part in allergy_text.replace(",", " ").split()):
            warnings.append("Allergy warning: review the patient's allergy history before selecting this medicine.")
        if medicine.drug_interactions:
            warnings.append(f"Drug interaction warning: {medicine.drug_interactions}")
        if medicine.contraindications:
            warnings.append(f"Contraindications: {medicine.contraindications}")
        if not warnings:
            warnings.append("No database warning found. Doctor review is still required.")
        return warnings

    def medicine_recommendations(self, db: Session, patient: Patient, symptoms: str) -> tuple[str, list[MedicineRecommendation]]:
        ranked = self._medicine_search(db, symptoms)
        recommendations = [
            MedicineRecommendation(
                medicine_id=med.id,
                medicine_name=med.medicine_name,
                generic_name=med.generic_name,
                why_recommended=(
                    f"Recommended for review because the medicine database matched: {', '.join(matched)}."
                    if matched
                    else "Included for doctor review from the medicine database."
                ),
                medicine_description=med.medicine_description or med.indications,
                matching_symptoms=matched,
                uses=", ".join(filter(None, [med.indications, med.therapeutic_category, med.common_diseases])),
                warnings=self._warnings_for(patient, med),
                alternative_medicines=med.alternative_medicines,
                rank_score=score,
            )
            for med, score, matched in ranked
        ]
        med_context = [
            {
                "name": med.medicine_name,
                "generic": med.generic_name,
                "symptoms_keywords": med.symptoms_keywords,
                "search_keywords": med.search_keywords,
                "medicine_description": med.medicine_description,
                "clinical_notes": med.clinical_notes,
                "common_diseases": med.common_diseases,
                "alternative_medicines": med.alternative_medicines,
                "indications": med.indications,
                "interactions": med.drug_interactions,
                "contraindications": med.contraindications,
                "rank_score": score,
                "matched_symptoms": matched,
            }
            for med, score, matched in ranked
        ]
        if not recommendations:
            return (
                "No medicines in the database matched these symptoms. Try broader or different symptom terms, "
                "or check that the medicine database has been imported.",
                recommendations,
            )

        prompt = f"""
The candidate medicines below were already selected and ranked from the clinic's own medicine database
by matching the patient's exact symptoms against symptoms_keywords, search_keywords, medicine_description,
common_diseases, clinical_notes, and indications. This ranking is authoritative and grounded in real data.

Your job is ONLY to:
1. Write a short doctor-facing clinical_note (1-3 sentences) about this symptom presentation.
2. For each candidate medicine_id, write a precise why_recommended explanation that cites the specific
   symptom keywords that matched and, if relevant, the patient's history.
3. Add any additional clinically relevant warnings for that medicine given this patient's allergy and
   chronic disease history, on top of the warnings already listed.

Do NOT introduce medicines that are not in the candidate list. Do NOT change the ranking or omit candidates.
Do NOT invent matching symptoms that are not supported by the medicine's database fields.

Patient context JSON:
{json.dumps(self.patient_context(db, patient), default=str)}

Current symptoms (exact text entered by the doctor):
{symptoms}

Ranked candidate medicines JSON (already ordered by relevance, do not reorder):
{json.dumps(med_context, default=str)}

Return strict JSON only, no prose outside the JSON, with this shape:
{{
  "clinical_note": "short doctor-facing review note",
  "recommendations": [
    {{
      "medicine_id": 1,
      "why_recommended": "explanation grounded in the exact matched symptom keywords and patient history",
      "extra_warnings": ["additional warning if any"]
    }}
  ]
}}
"""
        ai_result = self._complete_json(prompt)
        by_id = {item.medicine_id: item for item in recommendations}
        for item in ai_result.get("recommendations", []):
            medicine = by_id.get(item.get("medicine_id"))
            if not medicine:
                continue
            extra_warnings = [w for w in item.get("extra_warnings") or [] if w and w not in medicine.warnings]
            by_id[medicine.medicine_id] = medicine.model_copy(
                update={
                    "why_recommended": item.get("why_recommended") or medicine.why_recommended,
                    "warnings": medicine.warnings + extra_warnings,
                }
            )
        # Preserve the original database-grounded ranking order (exact match to symptoms);
        # only the text fields above are enriched by the model, never the order or the candidate set.
        recommendations = [by_id[item.medicine_id] for item in recommendations]
        clinical_note = ai_result.get("clinical_note") or (
            "Ranked medicines are grounded in the clinic medicine database and matched directly against the "
            "entered symptoms. Doctor review is required before selecting any medicine."
        )
        return clinical_note, recommendations

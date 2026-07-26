from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import AppointmentStatus, Role


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    role: Role


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: Role
    specialty: str | None = None


class UserRead(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: Role
    specialty: str | None

    model_config = ConfigDict(from_attributes=True)


class DoctorRead(BaseModel):
    id: int
    full_name: str
    specialty: str | None

    model_config = ConfigDict(from_attributes=True)


class PatientBase(BaseModel):
    name: str
    age: int | None = Field(default=None, ge=0, le=130)
    gender: str | None = None
    dob: date | None = None
    phone: str
    email: EmailStr | None = None
    address: str | None = None
    emergency_contact: str | None = None
    blood_group: str | None = None
    height_cm: float | None = Field(default=None, ge=0)
    weight_kg: float | None = Field(default=None, ge=0)
    allergies: str | None = None
    chronic_diseases: str | None = None
    notes: str | None = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(PatientBase):
    name: str | None = None
    phone: str | None = None


class PatientRead(PatientBase):
    id: int
    patient_code: str
    bmi: float | None
    photo_path: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VitalCreate(BaseModel):
    patient_id: int
    temperature_c: float | None = None
    pulse: int | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    oxygen_saturation: float | None = None
    respiratory_rate: int | None = None
    notes: str | None = None


class VitalRead(VitalCreate):
    id: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VisitCreate(BaseModel):
    patient_id: int
    symptoms: str
    diagnosis: str | None = None
    doctor_notes: str | None = None
    follow_up_date: date | None = None


class PrescriptionItemCreate(BaseModel):
    medicine_id: int | None = None
    medicine_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: str | None = None
    ai_suggested: bool = False
    doctor_approved: bool = True


class VisitRead(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    symptoms: str
    diagnosis: str | None
    doctor_notes: str | None
    ai_summary: str | None
    follow_up_date: date | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicineRead(BaseModel):
    id: int
    medicine_code: str
    medicine_name: str
    generic_name: str | None
    brand_name: str | None
    drug_class: str | None
    therapeutic_category: str | None
    indications: str | None
    dosage_form: str | None
    strength: str | None
    adult_dose: str | None
    pediatric_dose: str | None
    elderly_dose: str | None
    contraindications: str | None
    side_effects: str | None
    drug_interactions: str | None
    pregnancy_safety: str | None
    storage_conditions: str | None
    manufacturer: str | None
    prescription_required: bool
    stock_quantity: int
    notes: str | None
    symptoms_keywords: str | None
    search_keywords: str | None
    medicine_description: str | None
    clinical_notes: str | None
    common_diseases: str | None
    alternative_medicines: str | None

    model_config = ConfigDict(from_attributes=True)


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_date: date
    appointment_time: time
    visit_type: str = Field(pattern="^(New Consultation|Follow-up|Emergency|Review)$")
    priority: str = Field(pattern="^(Normal|High|Urgent)$")
    reason_for_visit: str
    notes: str | None = None
    follow_up_required: bool = False


class AppointmentUpdate(BaseModel):
    patient_id: int | None = None
    doctor_id: int | None = None
    appointment_date: date | None = None
    appointment_time: time | None = None
    visit_type: str | None = Field(default=None, pattern="^(New Consultation|Follow-up|Emergency|Review)$")
    priority: str | None = Field(default=None, pattern="^(Normal|High|Urgent)$")
    reason_for_visit: str | None = None
    notes: str | None = None
    status: AppointmentStatus | None = None


class AppointmentComplete(BaseModel):
    symptoms: str = "Consultation completed from appointment."
    diagnosis: str
    prescription: str | None = None
    doctor_notes: str | None = None
    ai_summary: str | None = None


class AppointmentRead(BaseModel):
    id: int
    token_number: str | None
    patient_id: int
    patient_code: str
    patient_name: str
    doctor_id: int | None
    doctor_name: str | None
    appointment_at: datetime
    appointment_date: date | None
    appointment_time: time | None
    visit_type: str | None
    priority: str | None
    reason_for_visit: str | None
    notes: str | None
    status: AppointmentStatus
    follow_up_required: bool


class AppointmentSummary(BaseModel):
    todays_appointments: int
    waiting_patients: int
    in_progress: int
    completed_today: int
    cancelled_today: int


class AppointmentNotification(BaseModel):
    message: str
    status: AppointmentStatus
    appointment_id: int
    token_number: str | None


class AiSymptomRequest(BaseModel):
    patient_id: int
    symptoms: str
    vitals: str | None = None


class AiMedicineRequest(BaseModel):
    patient_id: int
    symptoms: str
    diagnosis: str | None = None


class AiResponse(BaseModel):
    content: str
    safety_notice: str = "AI output is decision support only. A licensed doctor must review and approve all clinical decisions."


class MedicineRecommendation(BaseModel):
    medicine_id: int
    medicine_name: str
    generic_name: str | None = None
    why_recommended: str
    medicine_description: str | None = None
    matching_symptoms: list[str]
    uses: str | None = None
    warnings: list[str]
    alternative_medicines: str | None = None
    rank_score: int


class AiMedicineRecommendationResponse(AiResponse):
    patient_id: int
    current_symptoms: str
    recommendations: list[MedicineRecommendation]


class DashboardStats(BaseModel):
    todays_patients: int
    appointments: int
    pending_followups: int
    medicine_stock: int
    revenue: float


class ChatConversationCreate(BaseModel):
    title: str | None = None


class ChatConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=180)


class ChatMessageSend(BaseModel):
    conversation_id: int | None = None
    message: str = Field(min_length=1, max_length=4000)


class ChatMessageRead(BaseModel):
    id: int
    role: str
    content: str
    data_source: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatConversationRead(BaseModel):
    id: int
    title: str
    role: Role
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageRead] = []

    model_config = ConfigDict(from_attributes=True)


class ChatConversationSummary(BaseModel):
    id: int
    title: str
    role: Role
    updated_at: datetime
    last_message: str | None = None


class ChatSendResponse(BaseModel):
    conversation: ChatConversationRead
    answer: ChatMessageRead

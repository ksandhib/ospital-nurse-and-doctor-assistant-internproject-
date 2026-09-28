# AI ClinicOS

**Intelligent AI-Powered Clinic Management System**

AI ClinicOS is an intelligent, locally deployed clinic management system built with **FastAPI, SQLAlchemy, MySQL/SQLite, Ollama, and a responsive Vanilla HTML/CSS/JavaScript frontend**.

The system is designed to streamline clinical workflows between doctors and nurses while providing local AI-powered assistance for symptom analysis, medicine information, diagnosis support, prescriptions, and medical record management.

The application follows a **privacy-focused local AI architecture**, where the browser communicates with the FastAPI backend and the backend communicates with the local Ollama AI engine.

```text
Browser
   ↓
FastAPI Backend
   ↓
Local Ollama AI
   ↓
AI Response
   ↓
FastAPI
   ↓
Browser
```

No direct Ollama communication occurs from the frontend.

---

# 1. Project Overview

AI ClinicOS provides a centralized digital platform for managing clinic operations.

The system supports two primary roles:

```text
Doctor
Nurse
```

Each role receives a dedicated workflow based on their responsibilities.

### Nurse

Nurses can manage:

* Patient registration
* Patient information
* Vital signs
* Medical documents
* Appointments
* Medicine database imports
* Patient records

### Doctor

Doctors can manage:

* Patient search
* Electronic Medical Records
* Patient timelines
* Symptoms
* AI-assisted symptom analysis
* AI-assisted medicine information
* Diagnosis
* Prescriptions
* Medical reports
* PDF exports

---

# 2. Main Objectives

The primary objectives of AI ClinicOS are:

1. Digitize clinic workflows.
2. Reduce manual record management.
3. Centralize patient information.
4. Provide AI-assisted clinical decision support.
5. Maintain a structured electronic medical record.
6. Provide local AI processing through Ollama.
7. Reduce dependency on external AI APIs.
8. Provide searchable patient information.
9. Generate PDF and Excel reports.
10. Maintain a scalable backend architecture.

---

# 3. Core Features

## Authentication

* JWT authentication
* Password hashing
* Role-based access
* Doctor accounts
* Nurse accounts
* Protected API endpoints

---

## Nurse Workflow

Nurses can perform:

```text
Patient Registration
        ↓
Patient Information
        ↓
Vital Collection
        ↓
Document Upload
        ↓
Appointment Management
        ↓
Medicine Database Management
```

---

## Doctor Workflow

Doctors can perform:

```text
Patient Search
      ↓
Patient Profile
      ↓
EMR Timeline
      ↓
Symptom Review
      ↓
AI Analysis
      ↓
Doctor Review
      ↓
Diagnosis
      ↓
Prescription
      ↓
PDF Export
```

---

# 4. AI Features

AI ClinicOS integrates a locally running AI model through **Ollama**.

The AI layer can assist with:

* Symptom analysis
* Clinical information summarization
* Medicine explanations
* Clinical warnings
* Patient history summarization
* Diagnosis-support information
* Prescription-support information

The AI is designed as a **decision-support system**, not as an autonomous replacement for a qualified medical professional.

---

# 5. Local AI Architecture

The frontend never communicates directly with Ollama.

The architecture is:

```text
┌──────────────────────┐
│      Web Browser     │
│ HTML/CSS/JavaScript  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    FastAPI Backend   │
│ Authentication/API   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   AI Service Layer   │
│   Ollama Connector   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    Local Ollama      │
│      LLM Model       │
└──────────┬───────────┘
           │
           ▼
       AI Response
```

This design provides a clear separation between:

* Frontend
* Backend
* AI service
* Database
* Clinical workflows

---

# 6. Ollama Integration

AI ClinicOS uses Ollama as its local AI inference engine.

Default configuration:

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

Start Ollama:

```bash
ollama serve
```

Download the model:

```bash
ollama pull llama3.1
```

Verify installed models:

```bash
ollama list
```

---

# 7. AI Model Flexibility

The model can be changed through environment variables.

Example:

```env
OLLAMA_MODEL=llama3.1
```

Other locally available models can also be configured, depending on hardware and project requirements.

Examples may include:

```text
llama3.1
mistral
meditron
```

The application does not require an external AI API key for its core AI functionality.

---

# 8. Medicine Matching Architecture

AI ClinicOS separates deterministic medicine matching from generative AI.

The workflow is:

```text
Patient Symptoms
       ↓
Medicine Database
       ↓
Deterministic Matching
       ↓
Matched Medicines
       ↓
Ollama
       ↓
Additional Explanation
       ↓
Doctor Review
```

The medicine database is the primary source for medicine matching.

Ollama is used to enrich explanations and provide additional warnings rather than independently inventing or reordering the database-matched medicines.

This separation helps make the medicine-matching process more predictable and auditable.

---

# 9. Electronic Medical Record

The EMR system can maintain information such as:

```text
Patient
│
├── Personal Information
│
├── Vital Signs
│
├── Symptoms
│
├── Medical Documents
│
├── Appointments
│
├── Diagnoses
│
├── Prescriptions
│
└── Medical Timeline
```

Doctors can review the patient's historical information through a centralized timeline.

---

# 10. Patient Timeline

A patient's medical timeline can contain:

```text
Date
 ↓
Appointment
 ↓
Vitals
 ↓
Symptoms
 ↓
Diagnosis
 ↓
Prescription
 ↓
Documents
```

This provides doctors with a chronological view of patient interactions.

---

# 11. Database Architecture

AI ClinicOS supports:

### Development

```text
SQLite
```

### Production

```text
MySQL
```

SQLAlchemy provides the database abstraction layer, allowing the application to use the same application-level database architecture while changing the configured database URL.

Example SQLite:

```env
DATABASE_URL=sqlite:///./ai_clinicos.db
```

Example MySQL:

```env
DATABASE_URL=mysql+pymysql://clinic_user:clinic_password@localhost:3306/ai_clinicos
```

---

# 12. Database Design

The database uses normalized tables with relationships, foreign keys, and searchable indexes.

Possible entities include:

```text
users
patients
vitals
appointments
medical_documents
symptoms
diagnoses
prescriptions
medicines
medicine_symptoms
medical_records
```

Example relationship:

```text
User
 │
 ├── Doctor
 │
 └── Nurse

Patient
 │
 ├── Vitals
 ├── Appointments
 ├── Documents
 ├── Symptoms
 ├── Diagnoses
 └── Prescriptions
```

---

# 13. Project Structure

A typical project structure is:

```text
AI-ClinicOS/
│
├── backend/
│   │
│   ├── app/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── utils/
│   │   │
│   │   ├── main.py
│   │   └── seed.py
│   │
│   ├── .env
│   ├── requirements.txt
│   └── ai_clinicos.db
│
├── database/
│   └── migrations/
│       └── 001_initial_schema.sql
│
├── frontend/
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── assets/
│
└── README.md
```

---

# 14. Backend

The backend is built using **FastAPI**.

Responsibilities include:

* Authentication
* Patient management
* Appointment management
* Vital management
* EMR management
* Medicine management
* AI requests
* Report generation
* PDF generation
* Excel processing
* Database operations

The backend acts as the central control layer of the application.

---

# 15. API Architecture

The frontend communicates with the backend through REST APIs.

Example architecture:

```text
Frontend
   │
   ├── Authentication API
   ├── Patient API
   ├── Appointment API
   ├── Vital API
   ├── EMR API
   ├── Medicine API
   ├── AI API
   └── Report API
          │
          ▼
      FastAPI
          │
    ┌─────┴─────┐
    ▼           ▼
 Database      AI
               │
             Ollama
```

---

# 16. Authentication

AI ClinicOS uses JWT-based authentication.

Authentication workflow:

```text
Login
 ↓
Username / Email
 ↓
Password Verification
 ↓
Password Hash Validation
 ↓
JWT Token
 ↓
Protected API Requests
```

Passwords should never be stored as plain text.

---

# 17. Role-Based Access

The application has two primary roles:

```text
DOCTOR
NURSE
```

### Doctor

Access to clinical workflows and doctor-specific functionality.

### Nurse

Access to patient registration, vitals, appointments, documents, and supported administrative workflows.

The backend validates authorization instead of relying only on frontend restrictions.

---

# 18. Excel Medicine Import

The system supports medicine information through Excel files.

Example workflow:

```text
Excel File
    ↓
Upload
    ↓
Validation
    ↓
Data Processing
    ↓
Database
    ↓
Medicine Search / Matching
```

This allows the clinic's medicine database to be maintained without manually entering every medicine individually.

---

# 19. PDF Reports

The system supports PDF exports for relevant clinical records and reports.

Possible exports include:

* Patient summary
* Diagnosis
* Prescription
* Medical history
* Appointment information
* Clinical report

---

# 20. Excel Reports

Excel-compatible reports can be generated for supported administrative and medical data.

Example:

```text
Patient ID
Patient Name
Appointment Date
Doctor
Symptoms
Diagnosis
Prescription
Status
```

---

# 21. Local Development Setup

AI ClinicOS is configured to run locally with minimal external dependencies.

## Requirements

Recommended:

```text
Python 3.10+
FastAPI
SQLAlchemy
SQLite / MySQL
Ollama
Modern Web Browser
```

For production deployments:

```text
MySQL
```

can be used instead of SQLite.

---

# 22. Quick Local Start

Navigate to the backend:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the database and demo users:

```bash
python -m app.seed
```

Start FastAPI:

```bash
uvicorn app.main:app --reload
```

---

# 23. SQLite Configuration

The default configuration uses SQLite:

```env
DATABASE_URL=sqlite:///./ai_clinicos.db
```

This means the project can be started without installing MySQL.

The application automatically creates the required tables during startup.

---

# 24. Demo Accounts

Development/demo accounts:

### Doctor

```text
Email:
doctor@clinicos.example

Password:
Doctor@123
```

### Nurse

```text
Email:
nurse@clinicos.example

Password:
Nurse@123
```

These credentials should be changed or removed before any real deployment.

---

# 25. Frontend

The frontend is built using:

```text
HTML5
CSS3
JavaScript
```

No heavy frontend framework is required.

This keeps the interface lightweight and easy to deploy.

The frontend communicates with FastAPI through HTTP REST APIs.

---

# 26. Running the Frontend

The frontend can be opened directly:

```text
frontend/index.html
```

Alternatively, use a static development server such as VS Code Live Server.

Example:

```text
http://localhost:5500
```

The backend CORS configuration can allow the frontend development server.

---

# 27. MySQL Production Setup

Create the MySQL database using:

```sql
SOURCE database/migrations/001_initial_schema.sql;
```

Configure:

```env
DATABASE_URL=mysql+pymysql://clinic_user:clinic_password@localhost:3306/ai_clinicos
```

Then run:

```bash
python -m app.seed
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

For production, use a production-grade process manager and deployment configuration rather than development reload mode.

---

# 28. Ollama Production Setup

Install Ollama on the local machine.

Then:

```bash
ollama serve
```

Pull the model:

```bash
ollama pull llama3.1
```

Configure:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

The FastAPI backend will communicate with Ollama.

---

# 29. AI Failure Handling

If Ollama is unavailable, the entire application should not fail.

The backend can return a clear message such as:

```text
Local AI service is currently unavailable.

Please start Ollama and ensure the configured model is installed.
```

The deterministic medicine-matching functionality can continue independently of Ollama when the required database information is available.

---

# 30. Safety Architecture

AI ClinicOS is designed as a **clinical decision-support system**.

AI-generated information must be reviewed by an appropriately qualified doctor before being used for diagnosis or medication decisions.

The system should not be treated as an autonomous medical decision-maker.

The architecture therefore follows:

```text
Patient Data
     ↓
AI Analysis
     ↓
AI Recommendation / Explanation
     ↓
Doctor Review
     ↓
Doctor Decision
     ↓
Clinical Record
```

---

# 31. Privacy

Because Ollama runs locally, AI requests can remain within the organization's local infrastructure.

```text
Patient Data
     ↓
FastAPI
     ↓
Local Ollama
     ↓
Local AI Response
```

No external AI API key is required for the local AI functionality.

Production deployments should additionally implement:

* Encryption
* Strong authentication
* Role-based authorization
* Secure backups
* Audit logs
* Access controls
* Data retention policies
* Secure document storage
* Database security

---

# 32. Security Recommendations

Before production deployment:

* Change demo passwords.
* Generate a strong JWT secret.
* Restrict CORS origins.
* Enable HTTPS.
* Secure MySQL credentials.
* Protect uploaded documents.
* Validate file uploads.
* Apply authorization checks to every protected endpoint.
* Avoid logging sensitive patient information unnecessarily.
* Configure database backups.
* Apply appropriate access-control policies.

---

# 33. API Documentation

When FastAPI is running, interactive API documentation is normally available at:

```text
http://127.0.0.1:8000/docs
```

Alternative documentation:

```text
http://127.0.0.1:8000/redoc
```

These interfaces can be used during development and API testing.

---

# 34. Example Clinical AI Workflow

Example input:

```text
Patient reports fever, cough and sore throat
for two days.
```

The system can process the information:

```text
Symptoms
   ↓
Patient Record
   ↓
Medicine Database Matching
   ↓
AI Explanation
   ↓
Clinical Warnings
   ↓
Doctor Review
```

The final diagnosis and treatment decision remain with the qualified clinician.

---

# 35. Scalability

The current architecture is suitable for local deployments and can be expanded.

Future architecture:

```text
Frontend
    ↓
Load Balancer
    ↓
FastAPI Services
    ↓
PostgreSQL / MySQL
    ↓
AI Worker Layer
    ↓
Ollama / Local GPU
```

Additional services can later include:

* Redis
* Background task queues
* Object storage
* Vector databases
* Audit logging
* Monitoring
* Multi-clinic support

---

# 36. Future Enhancements

Possible future improvements include:

* Voice-based patient records
* Medical speech-to-text
* Doctor voice assistant
* Local medical RAG
* Medical document analysis
* Lab report analysis
* OCR
* Appointment reminders
* Advanced analytics
* Patient dashboards
* Multi-clinic management
* Hospital integration
* FHIR-compatible interoperability
* Audit trails
* Advanced role management
* GPU-accelerated local inference

---

# 37. Technology Stack

| Layer                | Technology              |
| -------------------- | ----------------------- |
| Frontend             | HTML5, CSS3, JavaScript |
| Backend              | FastAPI                 |
| ORM                  | SQLAlchemy              |
| Development Database | SQLite                  |
| Production Database  | MySQL                   |
| Authentication       | JWT                     |
| Password Security    | Password Hashing        |
| Local AI             | Ollama                  |
| AI Model             | Configurable Local LLM  |
| Reports              | PDF / Excel             |
| API                  | REST                    |
| Architecture         | Local / Privacy-Focused |

---

# 38. Project Architecture Summary

```text
                         AI ClinicOS
                              │
                 ┌────────────┴────────────┐
                 │                         │
             FRONTEND                  BACKEND
          HTML/CSS/JS                  FastAPI
                 │                         │
                 │             ┌───────────┼───────────┐
                 │             │           │           │
                 │       Authentication  Clinical     AI
                 │             │         Services    Service
                 │             │           │           │
                 │             │           ▼           ▼
                 │             │       Database     Ollama
                 │             │
                 │             ▼
                 │        SQLite / MySQL
                 │
                 └─────────────── REST API
```

---

# 39. Author & Developer

## Sandhib Kumar

**Author:** Sandhib Kumar

**Lead Developer:** Sandhib Kumar

**AI Engineer:** Sandhib Kumar

**Full-Stack Developer:** Sandhib Kumar

**System Architect:** Sandhib Kumar

**AI Architecture:** Sandhib Kumar

**Project Designer:** Sandhib Kumar

**Project Maintainer:** Sandhib Kumar

**Designed, Developed & Maintained by:** **Sandhib Kumar**

### Technical Contributions

Sandhib Kumar is responsible for the design and development of the AI ClinicOS platform, including:

* System architecture
* AI architecture
* Local LLM integration
* Ollama integration
* FastAPI backend
* REST API architecture
* Database architecture
* SQLAlchemy integration
* MySQL/SQLite support
* JWT authentication
* Password security
* Doctor workflow
* Nurse workflow
* Patient management
* EMR architecture
* AI symptom analysis
* Medicine matching architecture
* AI medicine explanations
* Prescription workflow
* PDF generation
* Excel integration
* Frontend development
* API integration
* Local deployment architecture
* Testing
* Security architecture
* Project documentation
* Future development roadmap

---

# 40. Developer Technology Profile

**Sandhib Kumar**

```text
AI Engineering
Full-Stack Development
Local AI
LLM Integration
Natural Language Processing
FastAPI
Python
SQLAlchemy
MySQL
SQLite
JavaScript
HTML
CSS
Ollama
REST APIs
Database Architecture
Automation
AI System Architecture
```

---

# 41. Copyright

```text
© 2026 Sandhib Kumar. All Rights Reserved.
```

AI ClinicOS is an original software project designed and developed by **Sandhib Kumar**.

Unauthorized copying, redistribution, modification, or commercial use of the project's source code, architecture, documentation, or associated materials is prohibited unless explicitly authorized by the author.

---

# 42. Project Identity

```text
╔══════════════════════════════════════════╗
║              AI ClinicOS                 ║
║                                          ║
║ Intelligent AI-Powered Clinic Management  ║
║                                          ║
║ Author & Developer: Sandhib Kumar        ║
║                                          ║
║ FastAPI • MySQL • SQLite • Ollama        ║
║ Local AI • EMR • Clinical Support        ║
╚══════════════════════════════════════════╝
```

**AI ClinicOS — Designed, Developed & Maintained by Sandhib Kumar.**

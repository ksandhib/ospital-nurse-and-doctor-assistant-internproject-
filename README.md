# AI ClinicOS

Intelligent AI-powered clinic management system built with FastAPI, MySQL, and a responsive vanilla HTML/CSS/JavaScript frontend.

## Features

- Two roles only: doctor and nurse
- JWT authentication with hashed passwords
- Nurse workflows: patient registration, vitals, documents, appointments, medicine Excel imports
- Doctor workflows: patient search, EMR timeline, AI symptom analysis, AI medicine suggestions, diagnosis, prescriptions, PDF export
- Normalized MySQL schema with foreign keys and searchable indexes
- Ollama (local AI) integration through a reusable backend service — the frontend never calls Ollama directly, every AI request flows Browser -> FastAPI -> Ollama -> Response
- PDF and Excel report exports

## Setup

The project ships pre-configured to run locally with **zero external services**: `backend/.env` defaults to a SQLite file database, so you can install dependencies and start the API immediately. Switch to MySQL for production by changing one line (`DATABASE_URL`) — no code changes needed, since SQLAlchemy talks to both through the same setting.

### Quick local start (SQLite, no MySQL required)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

That's it — `backend/.env` already has a working `DATABASE_URL=sqlite:///./ai_clinicos.db`. `python -m app.seed` creates the database file, all tables, and the two demo accounts below. The app also self-heals: even if you skip `seed` and go straight to `uvicorn`, every table is created automatically on startup.

Demo accounts:

- Doctor: `doctor@clinicos.example` / `Doctor@123`
- Nurse: `nurse@clinicos.example` / `Nurse@123`

Then open `frontend/index.html` in a browser, or serve the folder with any static file server (e.g. VS Code Live Server on port 5500, which is already in the default CORS allowlist).

### Switching to MySQL for production

1. Create the database:

```sql
SOURCE database/migrations/001_initial_schema.sql;
```

2. Update `backend/.env`:

```
database_url=mysql+pymysql://clinic_user:clinic_password@localhost:3306/ai_clinicos
```

3. Install and start Ollama, then pull a model:

```powershell
# https://ollama.com/download
ollama serve
ollama pull llama3.1
```

Set `OLLAMA_BASE_URL` / `OLLAMA_MODEL` in `backend/.env` if Ollama isn't running on the default `http://localhost:11434` with model `llama3.1`.

4. Re-run `python -m app.seed` against the new database, then `uvicorn app.main:app --reload`.

## Ollama

AI ClinicOS uses a local Ollama server as its only AI engine — no external AI API keys required. The backend calls `OLLAMA_BASE_URL` (default `http://localhost:11434`) using model `OLLAMA_MODEL` (default `llama3.1`). If Ollama isn't reachable, AI endpoints return a clear message telling you to start Ollama and pull the model, instead of failing the whole app or the medicine-matching feature. The exact medicine-matching results (which medicines match a set of symptoms, in what order) come from the clinic's own medicine database first and are always returned even if Ollama is offline — Ollama is only used to enrich the wording of the explanations and add extra clinical warnings, never to invent or reorder the matched medicines.

You can swap models by changing `OLLAMA_MODEL` (e.g. `llama3.1`, `mistral`, `meditron`, or any model you've pulled). Larger/medical-tuned models will generally give better clinical wording; the underlying symptom-to-medicine matching is deterministic regardless of model choice.

## Safety

AI output is decision support only. The prompts and API responses explicitly require doctor review and approval before any diagnosis or medication decision is finalized.

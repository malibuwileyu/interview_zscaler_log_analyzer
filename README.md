# Log Analyzer (Zscaler CSV) — Full‑Stack Take‑Home

Full‑stack web app that lets users:
- register/login
- upload Zscaler-style CSV web proxy logs
- view parsed events, anomaly flags, and a SOC-friendly summary timeline
- run **AI-assisted** review in small batches for per-event anomaly decisions + explanations

Repo layout:
- `backend/`: Flask API + Postgres (SQLAlchemy)
- `frontend/`: React (Vite) UI + Express production server that proxies `/api/*` to the backend
- `fixtures/`: sample Zscaler CSVs you can upload

---

## Local run (developer workstation assumed)

### 1) Start Postgres

This repo includes a `docker-compose.yml` for a local Postgres.

```bash
docker compose up -d
```

Default connection string used in examples below:
- `postgresql://postgres:postgres@localhost:5432/log_analyzer`

### 2) Run the backend (Flask)

From repo root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create environment variables (shell export or `.env` file). Minimum:

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/log_analyzer"
export JWT_SECRET_KEY="dev-secret-change-me"
export CORS_ORIGINS="*"
```

Optional (recommended):

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
export OPENAI_TIMEOUT_SECONDS="30"
export JWT_ACCESS_TOKEN_EXPIRES="3600"
export MAX_CONTENT_LENGTH_BYTES="26214400"
```

Start the backend:

```bash
python app_runner.py
```

Backend health check:

```bash
curl -s http://localhost:5000/health
```

### 3) Run the frontend (React)

In a second terminal:

```bash
cd frontend
npm install
```

For local dev, the UI calls `/api/*` and Vite proxies to `VITE_BACKEND_URL` (default is `http://localhost:5000`).

Optionally set:

```bash
cp env.example env.local
# edit env.local to set VITE_BACKEND_URL if you want something other than localhost
```

Start the dev server:

```bash
npm run dev
```

Open the UI at the Vite URL (printed in the terminal).

---

## Quick end‑to‑end test

1) Register + login in the UI
2) Upload a fixture:
   - `fixtures/zscaler_mixed_anomalies_2.csv` (mixed suspicious)
   - `fixtures/zscaler_mixed_anomalies_3.csv` (benign IT story but still has “triggers”)
3) Inspect:
   - **Summary** section (timeline + top talkers/domains)
   - **Logs** table (includes `anomaly_note` + `confidence_score`)
4) Run **AI Review** (bottom section) to get a per-event AI decision + short reason

---

## API endpoints (high level)

Auth:
- `POST /api/auth/register`
- `POST /api/auth/login`

Uploads:
- `POST /api/uploads/` (multipart form field `file`)
- `GET /api/uploads/`
- `GET /api/uploads/<upload_id>/logs?only_anomalies=0|1&limit=...`
- `GET /api/uploads/<upload_id>/summary?bucket_minutes=...`

Detections:
- `GET /api/detector/anomalies?upload_id=...&limit=...`
- `POST /api/detector/ai/review` (JWT) — AI review in small batches

---

## Anomaly detection approach (what’s “professional” here)

This project intentionally implements **two layers**:

### 1) Deterministic (rule-based) detector — first pass

Implemented in `backend/services/upload_service.py` during CSV parsing.

What it does:
- Flags individual rows based on simple triggers (e.g., high risk score, large outbound bytes)
- Produces:
  - `is_anomaly` (boolean)
  - `anomaly_note` (structured-ish string: rule + threshold + dest + context hint)
  - `confidence_score` (0–1), based on how far beyond thresholds the event is

Why this is “professional-ish”:
- Deterministic detection rules are common in SOC workflows (think SIEM detections).
- The output is explainable and repeatable.

What’s *not* production-grade (by design for the take-home):
- No tuning/calibration on real organization baselines (no FP/FN measurement).
- No time-window correlation rules (e.g., “N requests in T minutes”).
- No allowlists, enrichment, or threat intel integrations.

### 2) AI-assisted review — second pass (chunked)

Implemented in `backend/services/ai_detector_service.py` and exposed via:
- `POST /api/detector/ai/review`

What it does:
- Sends only a **small batch** of events at a time (default 25, max 50) to an LLM.
- Asks the model to behave like a SOC analyst and return **strict JSON** per event:
  - `is_anomalous` (yes/no)
  - `confidence` (0–1)
  - short `reason`
- The prompt explicitly tells the model not to treat “high risk” or “large bytes” as automatically malicious, and to use URL/domain context.

Why this is “professional-ish”:
- This mirrors real SOC augmentation: LLMs can provide **triage explanations** and context.
- The implementation is constrained (chunked input + strict output schema) to reduce model drift.

What’s *not* production-grade (again, by design for the take-home):
- No evaluation harness, rate limiting, cost controls, or full audit trail.
- No PII redaction policy (you should assume proxy logs can contain sensitive data).

---

## Notes / dev utilities

### Reset uploads/logs (keep users)

If you want to wipe old uploads/log entries (e.g., after changing parsing logic):

```bash
export DB_CLEAR=1
python backend/app_runner.py
```

Run once, then unset `DB_CLEAR` and restart normally.



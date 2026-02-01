## TODO – Backend MVP for Zscaler CSV Upload + Analysis

### Principles
- Ship an end-to-end happy path first (auth → upload → parse → view results).
- Keep routes thin, put logic in services, keep DB access in repositories.
- Prefer clear, explicit behavior over cleverness.

---

## 0) Unblock: app actually runs
- [ x] Fix `create_app()` bootstrapping
  - [ x] Create the Flask app instance (`app = Flask(__name__)`) before `app.config[...]`
  - [ x] Ensure `create_app()` returns the app and `__main__` runs it
- [x] Fix config defaults + types
  - [ x] `DATABASE_URL` default for local dev
  - [ x] JWT config: ensure expiry config doesn’t crash when env var missing
  - [ x] Add `MAX_CONTENT_LENGTH_BYTES` default
  - [ x] Choose `/api/uploads` (recommended) vs `/api/upload` and align docs/frontend

---

## 1) Database: reproducible local setup
- [ ] Fill `docker-compose.yml` with Postgres + env wiring
- [ ] Add `.env.example`
  - [ ] `DATABASE_URL`
  - [ ] `JWT_SECRET_KEY`
  - [ ] `CORS_ORIGINS`
  - [ ] `MAX_CONTENT_LENGTH_BYTES`
  - [ ] JWT expiry var(s)
- [ ] Add Flask-Migrate scaffolding and commit
  - [ ] `migrations/` directory checked in
  - [ ] Create initial migration for `User`, `Upload`, `LogEntry`
- [ ] Add a short `README.md` “Run locally” section (docker + migrate + run server)

---

## 2) Auth MVP (works end-to-end)
- [ ] Confirm `POST /api/auth/register` works
  - [ ] Validate inputs, return safe user payload
- [ ] Confirm `POST /api/auth/login` works
  - [ ] Return access token + safe user payload
- [ ] Add JWT-protected endpoint smoke test (e.g., `GET /api/uploads/` requires token)

---

## 3) Upload endpoints MVP
- [ ] Implement `POST /api/uploads/` (multipart file)
  - [ ] Require JWT (`@jwt_required()`)
  - [ ] Validate file exists
  - [ ] Return created Upload `{id, filename, status}`
- [ ] Implement `GET /api/uploads/`
  - [ ] Require JWT
  - [ ] Only return current user’s uploads
- [ ] Implement `GET /api/uploads/<upload_id>/logs?only_anomalies=1&limit=100`
  - [ ] Require JWT
  - [ ] Verify upload ownership (403 if not)
  - [ ] Support `only_anomalies` and `limit`

---

## 4) CSV parsing correctness + robustness (critical)
- [ ] Validate Zscaler CSV headers before parsing rows
  - [ ] Required: `datetime`, `clientip`, `url`, `action`, `sentbytes`, `app_risk_score`
  - [ ] If missing → return 400 with clear message
- [ ] Parse timestamps into real `datetime` objects (timezone-aware)
  - [ ] Decide format support (document in README)
- [ ] Handle large uploads safely
  - [ ] Batch DB insert/commit (avoid building huge `parsed_logs` list)
- [ ] Improve error handling
  - [ ] Don’t `raise e`; use `raise` after setting upload status
  - [ ] Ensure upload status always ends as `Completed` or `Failed`

---

## 5) “Detector” endpoints (bonus / but makes the UI nicer)
- [ ] Implement `GET /api/detector/anomalies?upload_id=<id>&limit=100`
  - [ ] Require JWT
  - [ ] Verify upload ownership when `upload_id` provided
  - [ ] If no `upload_id`, aggregate across user uploads (ok initially; optimize later)
- [ ] Add optional `POST /api/detector/preview` (debug endpoint)
  - [ ] Provide a sample “row” JSON → returns anomaly + reason

---

## 6) Match project requirements: anomaly explanation + confidence score
- [ ] Add `confidence_score` to `LogEntry` model (float 0–1 or 0–100)
- [ ] Compute confidence during parsing
  - [ ] Example: map risk score + bytes threshold to confidence
- [ ] Include confidence score in API responses (logs + anomalies endpoints)

---

## 7) Data “storage” decision (requirements mention uploads + storage)
Choose ONE and document it:

- [ ] Option A (fastest): **Store only parsed entries** (no raw file persisted)
  - [ ] Make it explicit in README
- [ ] Option B: **Store the raw uploaded file**
  - [ ] Save file to disk (e.g. `backend/uploads/<upload_id>.csv`)
  - [ ] Store file path on `Upload` model

---

## 8) Cleanup / consistency
- [ ] Fix inconsistent error response schemas (standardize `{error:{code,message}}`)
- [ ] Fix `UploadRepository.add_logs_bulk` typing (it takes list of mappings/dicts)
- [ ] Align model docstrings with schema (`risk_score` float vs int)
- [ ] Add `__init__.py` files (if not already) to stabilize imports

---

## 9) Minimal backend test / verification plan
- [ ] Smoke test script or curl commands in README:
  - [ ] Register user
  - [ ] Login → get token
  - [ ] Upload known-good Zscaler CSV
  - [ ] List uploads
  - [ ] Fetch logs (all + anomalies)
- [ ] Add at least 1 fixture Zscaler CSV (small) for manual testing

---
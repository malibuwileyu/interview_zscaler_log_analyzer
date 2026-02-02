## Backend TODO (remaining work)

This list is intentionally scoped to what’s *still missing* per `project_requirements.md` (plus AI anomaly detection).

### 1) File uploads **and storage**
- [ ] Decide and implement storage of the **original uploaded file**
  - [ ] Option A: store raw file contents in Postgres (simple, but increases DB size)
  - [ ] Option B: store file on disk/S3-like storage, keep a pointer in DB (more “real world”)
  - [ ] Option C: explicitly document “we store parsed entries only” (fastest, but doesn’t meet “storage” literally)

### 2) SOC-friendly analysis (timeline + learnings)
- [ ] Add an analysis endpoint that returns a **summary timeline** for an upload
  - [ ] Example outputs: “top talkers”, “top destinations”, “largest outbound transfers”, “risk score distribution”, “anomaly clusters”
  - [ ] (Optional) add simple grouping by `client_ip` + time window

### 3) Anomaly detection: confidence score + explanation
- [ ] Add `confidence_score` to stored anomalies (DB + API + frontend)
- [ ] Ensure each anomaly has a **human-readable explanation** (already partially present via `anomaly_note`)

### 4) AI-based detection (bonus)
- [ ] Implement AI/LLM-backed detector that can:
  - [ ] Explain **why** something is anomalous in context
  - [ ] Explain **why something is NOT anomalous** even if heuristics trigger (e.g., “legit software rollout” story)
  - [ ] Provide a confidence score
  - [ ] (Optional) produce a short per-upload summary for a SOC analyst

### 5) Local run instructions
- [ ] Add a simple local setup guide (README)
  - [ ] How to run Postgres (docker-compose or Railway instructions)
  - [ ] How to run backend + frontend locally

### 6) Document AI usage in building the project (required if you used AI)
- [ ] Add a short section describing where AI was used during development (and where it is used in the product, if at all)



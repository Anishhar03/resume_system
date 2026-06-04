# Technical Guide - Intelligent Resume Assistant

## 1. System Goal

Build a reliable hiring assistant that can:

- Parse resumes from PDF/text
- Retain resume + conversation context
- Answer hiring-focused questions
- Avoid hallucinations with strict guardrails
- Always produce structured machine-readable output

## 2. Core Technology Stack

- Backend framework: **Flask**
- Frontend: **Vanilla HTML/CSS/JS**
- PDF extraction: **PyPDF2**
- LLM provider: **Gemini API** via REST (`requests`)
- Environment handling: **python-dotenv**
- Data modeling: **Python dataclasses**

Rationale:

- Flask + Vanilla JS keeps the implementation lightweight and easy to review.
- PyPDF2 is sufficient for deterministic text extraction in a take-home scope.
- Dataclasses provide explicit schema and safer response handling.

## 3. Workflow and Architecture

### 3.1 Full Workflow
![Workflow](images/workflow-overview.svg)

### 3.2 Backend Architecture
![Architecture](images/backend-architecture.svg)

### 3.3 Agent Decision and Guardrail Loop
![Agent Loop](images/agent-decision-loop.svg)

## 4. Module-by-Module Internal Working

## 4.1 `backend/app.py` (API Orchestrator)

Responsibilities:

- Serves frontend static files
- Creates chat sessions
- Accepts resume upload or pasted text
- Invokes parsing and stores extracted data
- Routes chat messages through agent

Endpoints:

- `POST /api/session`
  - Returns a new UUID session id
- `POST /api/upload-resume`
  - Inputs:
    - `session_id`
    - `resume_file` (pdf/txt) OR `resume_text`
  - Output:
    - parsed resume JSON
- `POST /api/chat`
  - Inputs:
    - `session_id`
    - `message`
  - Output:
    - strict schema response

## 4.2 `backend/memory.py` (Context and State)

Data model:

- `SessionMemory`
  - `session_id`
  - `resume_text`
  - `extracted_data`
  - `conversation_history`
  - `intent_history`

Store:

- `MemoryStore` uses an in-memory dictionary for assignment simplicity.

Design trade-off:

- Pro: very simple and fast for demo
- Con: non-persistent; production should replace with Redis/Postgres

## 4.3 `backend/tools.py` (Internal Tools)

Implemented tools:

1. `extract_text_from_pdf`
   - Uses PyPDF2 page iteration and extraction.
2. `parse_resume_text`
   - Extracts:
     - name
     - email
     - phone
     - skills
     - education section
     - experience section
3. `match_required_skills`
   - Compares required skills from query to parsed skill set
   - Returns matched, missing, and score
4. `infer_intent`
   - Maps question to intent class:
     - summary
     - evaluation
     - skills
     - education
     - experience
5. `missing_data_fields`
   - Central missing-data detector used by guardrails

Why this matters:

- Tool outputs are deterministic and auditable.
- Agent can ground answers in extracted facts instead of pure generation.

## 4.4 `backend/agent.py` (Agentic Intelligence Layer)

Pipeline:

1. Infer user intent.
2. Run required tools (skill matcher for skill queries).
3. Build strict prompt with:
   - role constraints
   - extracted resume data
   - conversation history
   - missing-data hints
4. Try LLM JSON output.
5. If LLM fails, fallback to deterministic logic.
6. Enforce final schema.

Guardrails:

- Hard role: hiring assistant
- Prohibits fabricated claims
- Forces explicit missing data disclosure:
  - `"Not mentioned in resume"`

Confidence logic:

- Uses LLM confidence when valid
- fallback responses return conservative calibrated confidence values

## 4.5 `backend/llm.py` (Gemini Integration)

Implementation details:

- Calls endpoint:
  - `v1beta/models/{model}:generateContent`
- Uses API key from env
- Requests JSON output (`responseMimeType: application/json`)
- Handles network/parse failures safely by returning `None`

Failure strategy:

- If LLM is unavailable, the system still responds reliably through deterministic path.

## 4.6 `backend/models.py` (Response Contract)

`AgentResponse` ensures:

- `confidence` clamped to `[0,1]`
- `source` restricted to:
  - `resume`
  - `inference`
- output shape is always consistent

This guarantees compatibility for downstream consumers and evaluation scripts.

## 4.7 Frontend (`frontend/index.html`, `styles.css`, `app.js`)

UI features:

- Resume upload (file)
- Resume text paste mode
- Extracted JSON preview
- Chat panel for query/response

Client flow:

1. Create session on load
2. Upload resume and render parsed output
3. Send chat messages with `session_id`
4. Render structured assistant response

## 5. Response Schema and Reliability Policy

Every `/api/chat` output follows:

```json
{
  "answer": "string",
  "confidence": 0.0,
  "source": "resume | inference",
  "missing_data": []
}
```

Policy:

- If a field is unavailable in resume, answer includes:
  - `"Not mentioned in resume"`
- Missing fields are listed in `missing_data`.
- No unsupported or guessed claims.

## 6. Security and Operational Notes

- API keys are env-based (`.env`), never hardcoded.
- `.env.example` provides template only.
- Session memory is currently in-process; production should add:
  - persistence
  - auth
  - rate limiting
  - audit logs

## 7. Suggested Production Upgrades

- Replace heuristic parsing with robust extraction pipeline (layout-aware parsing).
- Add retriever + chunk-level citations from resume text.
- Add persistent memory (Redis/Postgres).
- Add automated tests:
  - parser unit tests
  - guardrail tests
  - response schema tests
- Containerize and deploy with CI checks on schema conformance.

## 8. Design Trade-offs

- Chosen simplicity over framework complexity to optimize maintainability and reviewability.
- Prioritized deterministic behavior under failures over maximum generative richness.
- Ensured assignment constraints are met without overengineering.


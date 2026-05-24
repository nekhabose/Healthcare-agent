# CLAUDE.md — CareGuard

CareGuard is a post-discharge care coordination AI agent. It calls patients after hospital discharge, conducts structured clinical check-ins via voice, and escalates concerns to the care team — reducing preventable hospital readmissions.

---

## Architecture

```
backend/
├── main.py                     # FastAPI app — middleware, routers, exception handlers
├── config.py                   # All settings via pydantic-settings (single source of truth)
├── database.py                 # SQLAlchemy async engine + session factory
├── exceptions.py               # Full domain exception hierarchy
│
├── models/
│   ├── db/                     # SQLAlchemy ORM models (source of truth for schema)
│   └── schemas/                # Pydantic schemas for API I/O
│
├── repositories/
│   ├── base.py                 # BaseRepository[M] — generic CRUD; subclass for queries
│   ├── patient.py
│   ├── discharge.py
│   ├── session.py
│   └── escalation.py
│
├── services/
│   ├── risk.py                 # RiskScoringService — pure function, no I/O
│   ├── discharge.py            # DischargeService — coordinates FHIR → risk → DB → queue
│   ├── outreach.py             # OutreachService — manages call lifecycle + callbacks
│   └── notification.py        # SNSNotifier / NoOpNotifier (swappable via BaseNotifier)
│
├── agent/
│   ├── care_agent.py           # CareAgent — drives Claude conversation loop
│   ├── tools/
│   │   ├── base.py             # BaseTool ABC — all tools inherit this
│   │   ├── registry.py         # ToolRegistry — collects tools, dispatches by name
│   │   ├── symptom.py          # assess_symptom
│   │   ├── medication.py       # check_medication_adherence
│   │   ├── escalation.py       # escalate_to_care_team
│   │   └── scheduling.py       # schedule_followup
│   └── protocols/
│       ├── base.py             # BaseProtocol ABC — shared preamble + checklist
│       ├── factory.py          # ProtocolFactory — maps hrrp_condition → protocol
│       ├── heart_failure.py
│       ├── pneumonia.py
│       ├── copd.py
│       └── orthopedic.py
│
├── fhir/
│   ├── client.py               # EpicFHIRClient — OAuth2 + async FHIR R4 requests
│   ├── parser.py               # DischargeParser — raw FHIR JSON → ParsedDischarge
│   └── schemas.py              # ParsedDischarge dataclass
│
├── api/
│   ├── deps.py                 # All FastAPI Depends() providers — single source of DI
│   ├── middleware/
│   │   ├── audit.py            # HIPAAAuditMiddleware — logs PHI access (never logs PHI)
│   │   └── error_handler.py    # Maps CareGuardError subclasses → HTTP status codes
│   └── routes/
│       ├── discharge.py        # POST /webhooks/discharge
│       ├── twilio_voice.py     # POST /twilio/twiml, WS /twilio/ws/{session_id}
│       └── dashboard.py        # GET /dashboard/patients, /escalations, /analytics
│
└── tasks/
    ├── celery_app.py           # Celery + SQS broker config
    └── outreach.py             # schedule_outreach_calls, initiate_call tasks

tests/
├── conftest.py                 # Shared fixtures (patient, discharge, mocks)
├── test_risk_scorer.py
├── test_tools.py
├── test_protocols.py
└── test_fhir_parser.py
```

---

## Key Design Patterns

### Repository Pattern
All DB access goes through a repository. Routes and services never use `db.execute()` directly.

```python
# Always do this:
repo = PatientRepository(db)
patient = await repo.get_by_epic_id(epic_id)

# Never do this in a route or service:
result = await db.execute(select(Patient).where(...))
```

### Service Layer
Services coordinate across repositories, FHIR, and external APIs. They contain all business logic. Routes are thin — they parse input, call one service method, and return the result.

### Tool + Registry Pattern
Every clinical tool inherits `BaseTool` and registers with `ToolRegistry`. To add a new tool:
1. Create `backend/agent/tools/your_tool.py` inheriting `BaseTool`
2. Register it in `OutreachService._build_registry()` or `CareAgent._build_registry()`
Nothing else changes.

### Protocol + Factory Pattern
Every HRRP condition has a `BaseProtocol` subclass. To add a new condition:
1. Create `backend/agent/protocols/your_condition.py`
2. Register it in `ProtocolFactory._registry`
Nothing else changes.

### Dependency Injection
All dependencies (DB sessions, services, repos, auth) are injected via `api/deps.py`.
Never instantiate services or repos inside route handlers.

### Error Handling
Raise domain exceptions from `exceptions.py`. The global handler in `error_handler.py` converts them to the right HTTP status. Never `raise HTTPException` from inside a service.

---

## HIPAA Rules — Non-Negotiable

- **Never log PHI.** Use `patient_id` (UUID) in logs, never name/DOB/phone.
- **All PHI fields** in the DB are suffixed `_enc` to signal app-layer encryption is required.
- **HIPAAAuditMiddleware** logs every request touching PHI paths. Do not disable it.
- **AWS BAA** must be signed before any real patient data touches AWS services.
- **Twilio BAA** and **Anthropic BAA** required before production use.
- Claude conversations may contain PHI — call recordings stored in KMS-encrypted S3 only.

---

## Running Locally

```bash
# Backend
cd backend
pip install -e ".[dev]"
cp .env.example .env          # fill in keys
uvicorn main:app --reload

# Celery worker
celery -A tasks.celery_app worker --loglevel=info

# Tests
pytest tests/ -v --cov=backend
```

---

## Environment Variables

See `backend/config.py` for the full list. Required for a running system:

| Variable | Description |
|---|---|
| `DATABASE_URL` | asyncpg PostgreSQL URL |
| `ANTHROPIC_API_KEY` | Claude API key |
| `TWILIO_ACCOUNT_SID` | Twilio account |
| `TWILIO_AUTH_TOKEN` | Twilio auth |
| `TWILIO_PHONE_NUMBER` | Outbound call number |
| `EPIC_FHIR_BASE_URL` | Epic FHIR R4 base URL |
| `EPIC_CLIENT_ID` | Epic OAuth client ID |
| `EPIC_PRIVATE_KEY_PATH` | Path to RSA private key for JWT assertion |
| `SNS_ESCALATION_TOPIC_ARN` | AWS SNS topic for care team alerts |
| `JWT_SECRET` | Secret for dashboard auth tokens |

---

## Adding a New Condition Protocol

1. Create `backend/agent/protocols/your_condition.py`:
   ```python
   from .base import BaseProtocol

   class YourConditionProtocol(BaseProtocol):
       condition_key = "your_condition"
       condition_specific_guidance = "..."

       @property
       def checklist(self) -> list[str]:
           return [...]
   ```
2. Register in `ProtocolFactory._registry`:
   ```python
   YourConditionProtocol.condition_key: YourConditionProtocol,
   ```
3. Add ICD-10 prefix → `"your_condition"` to `HRRP_ICD_MAP` in `fhir/client.py`.

---

## Change Log

| Date | Change |
|---|---|
| 2026-05-23 | Initial project scaffold — full backend architecture |
| 2026-05-23 | Agent layer: CareAgent, ToolRegistry, BaseTool, 4 clinical tools |
| 2026-05-23 | Protocol layer: BaseProtocol, ProtocolFactory, HF/Pneumonia/COPD/Ortho |
| 2026-05-23 | FHIR layer: EpicFHIRClient, DischargeParser |
| 2026-05-23 | Services: DischargeService, OutreachService, RiskScoringService, NotificationService |
| 2026-05-23 | API: discharge webhook, Twilio voice WebSocket, dashboard endpoints |
| 2026-05-23 | Tasks: Celery outreach scheduler |
| 2026-05-23 | Tests: risk scorer, tools, protocols |

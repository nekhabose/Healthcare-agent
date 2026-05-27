# CareGuard

**AI-powered post-discharge care coordination that prevents hospital readmissions.**

CareGuard automatically calls patients after hospital discharge, conducts structured clinical check-ins via voice AI, and escalates concerns to the care team — reducing the 79% of readmissions that are preventable.

---

## The Problem

Every year, CMS penalizes 2,400+ hospitals totalling **$320M** for excess readmissions in six conditions: heart failure, AMI, pneumonia, COPD, hip/knee replacement, and CABG. Up to 79% of these readmissions are preventable — they happen because patients leave the hospital without adequate follow-up support.

**CareGuard gives every discharged patient a 5-touch outreach sequence at exactly the right moments** (24h, 72h, 7d, 14d, 30d), prioritized by readmission risk level.

---

## How It Works

```
1. Epic fires a discharge webhook → CareGuard ingests FHIR data
2. Patient is risk-scored (high/medium/low) in seconds
3. AI agent calls patient at 24 hours post-discharge
4. Agent conducts a structured, condition-specific check-in via voice
5. Clinical tools detect symptoms, check adherence, detect red flags
6. Urgent findings trigger immediate care team escalation via SNS
7. Care coordinators review the dashboard; all calls logged with transcripts
8. Monthly analytics show readmission rate reduction and ROI
```

---

## Architecture

```
Epic EHR (FHIR R4)
       │ Discharge webhook
       ▼
FastAPI Backend (AWS ECS)
├── DischargeService     — FHIR pull → risk scoring → DB → task queue
├── CareAgent            — Claude claude-sonnet-4-6 + tool use conversation loop
│   ├── SymptomTool      — records symptoms, determines escalation level
│   ├── MedicationTool   — checks adherence per medication, identifies barriers
│   ├── EscalationTool   — fires care team alert via SNS
│   └── SchedulingTool   — queues follow-up appointment coordination
├── ProtocolFactory      — condition-specific check-in protocols (HF, COPD, etc.)
└── OutreachService      — Twilio ConversationRelay voice call lifecycle

AWS Infrastructure (HIPAA-eligible)
├── RDS PostgreSQL (KMS encrypted)   — patient data, sessions, escalations
├── S3 (KMS encrypted)               — discharge documents, call recordings
├── SQS + Celery                     — outreach call scheduling
├── SNS                              — care team escalation alerts
└── CloudTrail                       — PHI access audit log
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async |
| AI Agent | Provider-agnostic — Claude (Anthropic) or DeepSeek v3/v4 via OpenAI-compatible API |
| Voice | Twilio ConversationRelay (STT + TTS + WebSocket) |
| EHR Integration | Epic FHIR R4 via OAuth 2.0 JWT assertion |
| Database | PostgreSQL (AWS RDS, KMS-encrypted) |
| Task Queue | Celery + AWS SQS |
| Alerts | AWS SNS + SES |
| Infrastructure | AWS ECS Fargate, VPC, CloudTrail |

---

## Clinical Protocols

CareGuard includes condition-specific check-in protocols for every CMS HRRP-penalized condition:

| Condition | Key Monitoring Areas |
|---|---|
| **Heart Failure** | Daily weights, edema, dyspnea, diuretic adherence |
| **Pneumonia** | Fever pattern, cough changes, antibiotic adherence, hydration |
| **COPD** | Rescue inhaler use, sputum changes, O2 saturation, inhaler technique |
| **Hip/Knee Replacement** | Wound signs, DVT screening, blood thinner adherence, PT attendance |
| **AMI / CABG** | Chest pain, activity tolerance, cardiac medication adherence |

### Escalation Tiers

| Level | Trigger | Response |
|---|---|---|
| **Urgent** | Chest pain, breathing difficulty, stroke signs, severity ≥9/10 | 911 guidance + immediate care team page |
| **High** | Symptom severity 7–8/10, critical medication missed | Provider call within 2 hours |
| **Medium** | Non-adherence (barrier identified), no follow-up scheduled | Care coordinator follow-up next business day |

---

## Business Case

For a 300-bed hospital with 15% CHF readmission rate:

| Metric | Value |
|---|---|
| Monthly CHF discharges | ~120 |
| Current readmissions | 18/month |
| Agent target reduction | 25% |
| Prevented readmissions | ~4–5/month |
| Revenue preserved | **$68,400/month** |
| Agent cost (Growth tier) | $720/month |
| **Net monthly gain** | **~$67,680** |
| **ROI** | **~94x** |

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- AWS account with HIPAA BAA signed
- Twilio account with HIPAA BAA
- Anthropic API key with HIPAA BAA
- Epic FHIR sandbox credentials (`open.epic.com`)

### Local Setup

```bash
# 1. Clone and install
git clone https://github.com/your-org/careguard
cd careguard/backend
pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Fill in required values — see config.py for full list

# 3. Run database migrations
alembic upgrade head

# 4. Start the API
uvicorn main:app --reload --port 8000

# 5. Start the Celery worker (separate terminal)
celery -A tasks.celery_app worker --loglevel=info
```

### Running Tests

```bash
pytest tests/ -v --cov=backend --cov-report=term-missing
```

---

## Project Structure

```
careguard/
├── backend/
│   ├── main.py               # FastAPI app entrypoint
│   ├── config.py             # All settings (pydantic-settings)
│   ├── database.py           # Async SQLAlchemy engine
│   ├── exceptions.py         # Domain exception hierarchy
│   ├── agent/                # Claude agent, tools, protocols
│   ├── api/                  # Routes, middleware, DI providers
│   ├── fhir/                 # Epic FHIR client and parser
│   ├── models/               # DB models (ORM) + API schemas (Pydantic)
│   ├── repositories/         # Data access layer
│   ├── services/             # Business logic layer
│   └── tasks/                # Celery async tasks
├── tests/                    # Pytest test suite
├── Idea.md                   # Healthcare AI agent research & ideas
├── plan.md                   # Detailed implementation plan
├── CLAUDE.md                 # Developer guide for this codebase
└── README.md                 # This file
```

---

## HIPAA Compliance

CareGuard is built HIPAA-first:

- **PHI never in logs** — all log statements use patient UUIDs, never names or identifiers
- **Encryption at rest** — AWS KMS on all RDS and S3 resources
- **Encryption in transit** — TLS 1.3 on all connections, Twilio media encrypted
- **Audit logging** — every request touching PHI is logged to CloudTrail via `HIPAAAuditMiddleware`
- **BAAs required** — AWS, Twilio, and Anthropic all offer HIPAA BAAs; sign before any PHI flows
- **Role-based access** — JWT auth on all dashboard endpoints; principle of least privilege on all IAM policies

---

## Extending the System

### Adding a New Condition Protocol

1. Create `backend/agent/protocols/your_condition.py` inheriting `BaseProtocol`
2. Add to `ProtocolFactory._registry` in `factory.py`
3. Add ICD-10 codes to `HRRP_ICD_MAP` in `fhir/client.py`

### Adding a New Clinical Tool

1. Create `backend/agent/tools/your_tool.py` inheriting `BaseTool`
2. Register it in `OutreachService` inside `CareAgent._build_registry()`

### Switching LLM Providers

Set `LLM_PROVIDER=claude` or `LLM_PROVIDER=deepseek` in `.env` — no code changes required.
Both providers go through the unified `LLMClient` interface in `backend/agent/llm/`.
To add a new provider, subclass `LLMClient`, implement `create_message()`, and register it in `factory.py`.

**HIPAA note:** Anthropic offers a HIPAA BAA. DeepSeek does **not** currently — do not route PHI through DeepSeek in production until a BAA is signed.

### Adding a New Repository Query

Add a method to the relevant `*Repository` class. Never write raw SQL in services or routes.

---

## Roadmap

- [ ] Alembic database migrations
- [ ] SMS fallback when call goes unanswered
- [ ] Epic SMART on FHIR launch (embed dashboard in EHR chart)
- [ ] Epic In-Basket alert on escalation
- [ ] AMI and CABG condition protocols
- [ ] Application-layer PHI encryption (Fernet)
- [ ] Frontend care coordinator dashboard (React)
- [ ] Readmission rate analytics with before/after comparison

---

## License

Proprietary. All rights reserved.

---

*Built with [Claude](https://claude.ai) · Anthropic SDK · FastAPI · Twilio ConversationRelay · Epic FHIR R4*

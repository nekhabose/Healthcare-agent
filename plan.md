# Implementation Plan: Post-Discharge Care Coordination Agent

## Overview

An AI agent that automatically contacts patients after hospital discharge, conducts structured clinical check-ins via voice and SMS, identifies early warning signs, and escalates to the care team — reducing preventable readmissions and CMS HRRP penalties.

**Target buyer:** Hospital systems  
**ROI hook:** Every prevented readmission saves the hospital ~$15,200 in lost revenue + avoids CMS penalty (up to 3% of all Medicare payments)  
**Penalized conditions:** Heart failure, AMI, pneumonia, COPD, hip/knee replacement, CABG surgery

---

## Architecture Overview

```
Epic EHR (FHIR R4)
    │ Discharge event webhook
    ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Backend (AWS ECS)               │
│                                                     │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────┐ │
│  │ FHIR Client │   │ Scheduler    │   │ Dashboard│ │
│  │ (discharge  │   │ (outreach    │   │ API      │ │
│  │  data pull) │   │  timing)     │   │          │ │
│  └──────┬──────┘   └──────┬───────┘   └────┬─────┘ │
│         │                 │                │       │
│         ▼                 ▼                ▼       │
│  ┌─────────────────────────────────────────────┐   │
│  │          Claude claude-sonnet-4-6 Agent (tool use)     │   │
│  │  Tools: assess_symptoms, check_adherence,   │   │
│  │          escalate, schedule_followup         │   │
│  └────────────────────┬────────────────────────┘   │
│                       │                            │
│         ┌─────────────┴─────────────┐              │
│         ▼                           ▼              │
│  Twilio ConversationRelay      SMS / Email          │
│  (outbound voice calls)        (follow-up msgs)     │
└─────────────────────────────────────────────────────┘
         │                            │
         ▼                            ▼
  AWS RDS PostgreSQL            AWS SNS / SES
  (patient sessions,            (care team alerts)
   conversation logs,
   outcomes tracking)
         │
         ▼
  AWS S3 (encrypted)
  (discharge documents,
   conversation recordings)
```

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Backend API | Python + FastAPI | Async support for WebSocket (Twilio), fast development |
| AI Agent | Claude claude-sonnet-4-6 via Anthropic SDK | Best clinical reasoning, tool use, long context for patient history |
| Voice | Twilio ConversationRelay | Handles STT/TTS automatically; direct LLM integration |
| SMS | Twilio Messaging API | Appointment reminders, async follow-ups |
| EHR Integration | Epic FHIR R4 (via `fhirclient` Python library) | Standard interface; covers 35%+ of US hospitals |
| Database | AWS RDS PostgreSQL (encrypted) | HIPAA-eligible, relational for patient/session data |
| File Storage | AWS S3 (KMS-encrypted) | HIPAA-eligible; discharge documents, call recordings |
| Task Queue | AWS SQS + Celery | Schedule outreach calls at 24h, 72h, 7d, 14d, 30d intervals |
| Notifications | AWS SNS + SES | Care team escalation alerts |
| Frontend Dashboard | React + TypeScript + Tailwind | Care coordinator interface |
| Infrastructure | AWS ECS (Fargate) + VPC | HIPAA-eligible containerized deployment |
| Secrets | AWS Secrets Manager | Store API keys, FHIR tokens; never in env vars |
| Audit Logging | AWS CloudTrail + CloudWatch | PHI access audit trail (HIPAA requirement) |

---

## Project Structure

```
healthcare-agent/
├── backend/
│   ├── main.py                    # FastAPI app entrypoint
│   ├── config.py                  # Settings, env vars via Secrets Manager
│   ├── api/
│   │   ├── routes/
│   │   │   ├── discharge.py       # Webhook from Epic on patient discharge
│   │   │   ├── twilio_voice.py    # Twilio TwiML + WebSocket handler
│   │   │   ├── twilio_sms.py      # Inbound SMS handling
│   │   │   └── dashboard.py       # Care coordinator API endpoints
│   │   └── middleware/
│   │       ├── auth.py            # JWT auth for dashboard users
│   │       └── hipaa_audit.py     # Log all PHI access to CloudTrail
│   ├── agent/
│   │   ├── claude_agent.py        # Claude client + tool use orchestration
│   │   ├── tools/
│   │   │   ├── symptom_assessment.py   # assess_symptoms tool
│   │   │   ├── medication_check.py     # check_adherence tool
│   │   │   ├── escalation.py           # escalate_to_care_team tool
│   │   │   └── scheduling.py           # schedule_followup tool
│   │   └── protocols/
│   │       ├── base_protocol.py        # Core post-discharge check-in flow
│   │       ├── heart_failure.py        # HF-specific symptom protocol
│   │       ├── pneumonia.py            # Pneumonia-specific protocol
│   │       ├── copd.py                 # COPD-specific protocol
│   │       └── orthopedic.py           # Hip/knee replacement protocol
│   ├── fhir/
│   │   ├── client.py              # Authenticated Epic FHIR R4 client
│   │   ├── discharge_parser.py    # Extract discharge summary, meds, dx, follow-ups
│   │   └── models.py              # Pydantic models for FHIR resources
│   ├── models/
│   │   ├── patient.py             # Patient DB model
│   │   ├── outreach.py            # Outreach session model
│   │   ├── conversation.py        # Conversation turn model
│   │   └── escalation.py         # Escalation event model
│   ├── tasks/
│   │   ├── celery_app.py          # Celery + SQS broker config
│   │   └── outreach_scheduler.py  # Schedule outreach at discharge + intervals
│   └── notifications/
│       ├── care_team_alert.py     # SNS/SES notifications on escalation
│       └── sms.py                 # Patient SMS via Twilio
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx      # Patient list + risk indicators
│   │   │   ├── PatientDetail.tsx  # Conversation history + escalations
│   │   │   └── Analytics.tsx      # Readmission rate trends, ROI reports
│   │   └── components/
│   │       ├── RiskBadge.tsx      # High/Medium/Low risk indicator
│   │       ├── ConversationLog.tsx # Transcript of AI calls
│   │       └── EscalationCard.tsx  # Flagged escalation events
│   └── package.json
├── infrastructure/
│   ├── terraform/                 # AWS ECS, RDS, S3, SQS, VPC setup
│   └── docker/
│       └── Dockerfile
└── tests/
    ├── test_claude_agent.py
    ├── test_fhir_parser.py
    └── test_escalation.py
```

---

## Phase 1: Foundation (Weeks 1–3)

**Goal:** HIPAA-compliant infrastructure running, Epic FHIR integration pulling real discharge data.

### 1.1 AWS Infrastructure Setup
- Create AWS account and sign HIPAA BAA via AWS Artifact (self-service, no cost)
- Set up VPC with private subnets; no public access to database or internal services
- Deploy RDS PostgreSQL with KMS encryption at rest
- Configure S3 bucket with KMS encryption + bucket policy blocking public access
- Enable CloudTrail for all API calls (required for HIPAA audit log)
- Store all secrets (API keys, DB passwords) in AWS Secrets Manager

### 1.2 Database Schema
```sql
-- Core tables

CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    epic_patient_id VARCHAR NOT NULL UNIQUE,
    mrn VARCHAR,
    first_name VARCHAR NOT NULL,  -- encrypted at application layer
    last_name VARCHAR NOT NULL,   -- encrypted at application layer
    phone VARCHAR NOT NULL,       -- encrypted at application layer
    date_of_birth DATE,
    risk_score INTEGER,           -- 0-100, calculated at discharge
    risk_level VARCHAR,           -- 'high', 'medium', 'low'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE discharges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    discharge_date DATE NOT NULL,
    primary_diagnosis_code VARCHAR,    -- ICD-10
    primary_diagnosis_name VARCHAR,
    hrrp_condition VARCHAR,            -- 'heart_failure', 'ami', 'pneumonia', etc.
    discharge_summary_s3_key VARCHAR,  -- S3 path to encrypted discharge doc
    medications JSONB,                 -- Array of {name, dose, frequency, instructions}
    followup_appointments JSONB,       -- Array of {provider, specialty, date, location}
    discharge_instructions TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE outreach_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id),
    discharge_id UUID REFERENCES discharges(id),
    scheduled_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    channel VARCHAR NOT NULL,          -- 'voice', 'sms'
    status VARCHAR DEFAULT 'scheduled', -- 'scheduled', 'in_progress', 'completed', 'failed', 'no_answer'
    outreach_number INTEGER,           -- 1=24h, 2=72h, 3=7d, 4=14d, 5=30d
    twilio_call_sid VARCHAR,
    recording_s3_key VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE conversation_turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES outreach_sessions(id),
    role VARCHAR NOT NULL,             -- 'agent', 'patient'
    content TEXT NOT NULL,
    tool_calls JSONB,                  -- Claude tool calls made in this turn
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES outreach_sessions(id),
    patient_id UUID REFERENCES patients(id),
    severity VARCHAR NOT NULL,         -- 'urgent', 'high', 'medium'
    reason VARCHAR NOT NULL,
    symptoms_flagged JSONB,
    notified_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 1.3 Epic FHIR R4 Integration

**Authentication:** OAuth 2.0 client credentials flow for system-to-system access.

```python
# backend/fhir/client.py
import httpx
from fhirclient import client as fhir_client
from fhirclient.models import patient, medicationrequest, condition, documentreference

class EpicFHIRClient:
    def __init__(self, base_url: str, client_id: str, private_key: str):
        self.base_url = base_url
        self.client_id = client_id
        self.private_key = private_key
        self._access_token = None

    async def get_discharge_data(self, epic_patient_id: str) -> dict:
        """Pull all relevant data for a discharged patient."""
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as http:
            # Fetch in parallel
            patient_data, medications, conditions, documents, appointments = await asyncio.gather(
                http.get(f"{self.base_url}/Patient/{epic_patient_id}", headers=headers),
                http.get(f"{self.base_url}/MedicationRequest?patient={epic_patient_id}&status=active", headers=headers),
                http.get(f"{self.base_url}/Condition?patient={epic_patient_id}&category=encounter-diagnosis", headers=headers),
                http.get(f"{self.base_url}/DocumentReference?patient={epic_patient_id}&type=18842-5", headers=headers),  # 18842-5 = discharge summary LOINC
                http.get(f"{self.base_url}/Appointment?patient={epic_patient_id}&status=booked&date=ge{today}", headers=headers),
            )

        return DischargeParser.parse(patient_data.json(), medications.json(),
                                     conditions.json(), documents.json(), appointments.json())
```

**Discharge webhook:** Epic can send an ADT (Admit/Discharge/Transfer) HL7 message or FHIR Subscription notification when a patient is discharged. Register a FHIR Subscription on `Encounter.status = finished`.

```python
# backend/api/routes/discharge.py
@router.post("/webhook/discharge")
async def handle_discharge_event(payload: dict, background_tasks: BackgroundTasks):
    """Receives Epic FHIR Subscription notification on patient discharge."""
    epic_patient_id = payload["subject"]["reference"].split("/")[1]
    encounter_id = payload["id"]

    # Pull full discharge data from FHIR
    discharge_data = await fhir_client.get_discharge_data(epic_patient_id)

    # Persist patient + discharge
    patient = await PatientService.upsert(discharge_data)

    # Calculate readmission risk score (0-100)
    risk_score = RiskScorer.score(discharge_data)

    # Schedule outreach calls in background
    background_tasks.add_task(OutreachScheduler.schedule, patient.id, risk_score)

    return {"status": "accepted"}
```

### 1.4 Risk Stratification
Rule-based initial scorer (can upgrade to ML model later):

```python
class RiskScorer:
    HRRP_CONDITIONS = ["heart_failure", "ami", "pneumonia", "copd", "hip_knee", "cabg"]

    @staticmethod
    def score(discharge_data: DischargeData) -> int:
        score = 0
        # Prior readmissions (strongest predictor)
        score += min(discharge_data.prior_readmissions_90d * 15, 30)
        # HRRP condition (CMS-penalized)
        if discharge_data.hrrp_condition:
            score += 25
        # Polypharmacy (>5 medications)
        if len(discharge_data.medications) > 5:
            score += 10
        # Age
        if discharge_data.age > 75:
            score += 10
        # No follow-up appointment scheduled
        if not discharge_data.followup_appointments:
            score += 15
        # Social risk (lives alone, no caregiver)
        if discharge_data.lives_alone:
            score += 10
        return min(score, 100)
```

---

## Phase 2: AI Agent Core (Weeks 4–7)

**Goal:** Claude agent conducting real clinical conversations via voice with proper tool use, escalation, and condition-specific protocols.

### 2.1 Claude Agent with Tool Use

```python
# backend/agent/claude_agent.py
import anthropic
from .tools import TOOL_DEFINITIONS, ToolExecutor

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a care coordinator for {hospital_name}, calling to check on {patient_first_name} 
after their recent hospital discharge on {discharge_date}.

Your goals:
1. Assess how the patient is feeling and identify any concerning symptoms
2. Confirm they are taking their medications as prescribed
3. Confirm their follow-up appointment is scheduled
4. Escalate immediately if you detect red-flag symptoms

Patient context:
- Primary diagnosis: {diagnosis}
- Discharge medications: {medications}
- Follow-up appointments: {followup_appointments}
- Discharge instructions summary: {instructions_summary}

Conversation rules:
- Be warm, empathetic, and speak in plain language (6th-grade reading level)
- Ask one question at a time — do not overwhelm the patient
- Use the assess_symptoms tool when the patient reports any symptom
- Use the check_medication_adherence tool after discussing each medication
- Use the escalate_to_care_team tool immediately if the patient reports chest pain, 
  difficulty breathing, sudden weakness, or a symptom severity ≥ 8/10
- Use the schedule_followup tool if no appointment exists
- End the call gracefully after completing the full protocol

You are NOT diagnosing or treating. You are identifying concerns for the care team."""


async def run_conversation(session: OutreachSession, discharge: Discharge,
                           patient: Patient) -> list[ConversationTurn]:
    messages = []
    tool_executor = ToolExecutor(session, discharge, patient)

    # Opening message
    opening = f"Hello, may I speak with {patient.first_name}? ... Hi {patient.first_name}, " \
              f"this is your care team calling from {discharge.hospital_name} to check in " \
              f"on how you're doing since coming home from the hospital."
    messages.append({"role": "assistant", "content": opening})

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=SYSTEM_PROMPT.format(
                hospital_name=discharge.hospital_name,
                patient_first_name=patient.first_name,
                discharge_date=discharge.discharge_date,
                diagnosis=discharge.primary_diagnosis_name,
                medications=format_medications(discharge.medications),
                followup_appointments=format_appointments(discharge.followup_appointments),
                instructions_summary=discharge.instructions_summary,
            ),
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        # Handle tool calls
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = await tool_executor.execute(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue

        # Regular message — send to patient via Twilio
        agent_text = extract_text(response.content)
        messages.append({"role": "assistant", "content": agent_text})
        await TwilioService.send_to_call(session.twilio_call_sid, agent_text)

        if response.stop_reason == "end_turn" or is_goodbye(agent_text):
            break

        # Wait for patient response (injected by WebSocket handler)
        patient_text = await session.wait_for_patient_input()
        if patient_text:
            messages.append({"role": "user", "content": patient_text})

    return messages
```

### 2.2 Clinical Tools

```python
# backend/agent/tools/symptom_assessment.py

TOOL_DEFINITIONS = [
    {
        "name": "assess_symptom",
        "description": "Record a symptom the patient has reported and determine escalation level.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symptom": {"type": "string", "description": "Symptom name (e.g., 'shortness of breath', 'chest pain', 'swelling')"},
                "severity": {"type": "integer", "description": "Patient-reported severity 1-10"},
                "duration": {"type": "string", "description": "How long the symptom has been present"},
                "context": {"type": "string", "description": "Additional context the patient provided"}
            },
            "required": ["symptom", "severity"]
        }
    },
    {
        "name": "check_medication_adherence",
        "description": "Log whether the patient is taking a specific medication as prescribed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "medication_name": {"type": "string"},
                "taking_as_prescribed": {"type": "boolean"},
                "barrier": {"type": "string", "description": "If not taking, what is the reason (cost, side effects, confusion, etc.)"}
            },
            "required": ["medication_name", "taking_as_prescribed"]
        }
    },
    {
        "name": "escalate_to_care_team",
        "description": "Alert the care team immediately about a concerning finding.",
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {"type": "string", "enum": ["urgent", "high", "medium"],
                             "description": "urgent=call 911 or ER now; high=provider call within 2h; medium=flag for next business day"},
                "reason": {"type": "string", "description": "Clear clinical reason for escalation"},
                "symptoms": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["severity", "reason"]
        }
    },
    {
        "name": "schedule_followup",
        "description": "Create or confirm a follow-up appointment for the patient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "appointment_type": {"type": "string", "description": "e.g., 'primary care', 'cardiology', 'pharmacy review'"},
                "urgency": {"type": "string", "enum": ["within_24h", "within_7d", "within_14d", "within_30d"]}
            },
            "required": ["appointment_type", "urgency"]
        }
    }
]
```

**Escalation logic:**

| Symptom | Severity Threshold | Escalation Level |
|---|---|---|
| Chest pain / pressure | Any | **Urgent** (911 guidance + immediate page) |
| Shortness of breath | ≥ 6/10 | **Urgent** |
| Sudden severe headache | Any | **Urgent** |
| Signs of stroke (FAST) | Any | **Urgent** |
| New/worsening shortness of breath | 4–5/10 | **High** (provider call within 2h) |
| Weight gain > 2 lbs/day (HF) | — | **High** |
| Wound signs of infection | Any | **High** |
| Medication not being taken | — | **Medium** (pharmacist outreach) |
| No follow-up appointment scheduled | — | **Medium** (schedule coordination) |

### 2.3 Twilio ConversationRelay Integration

```python
# backend/api/routes/twilio_voice.py
from fastapi import APIRouter, WebSocket
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream

router = APIRouter()

@router.post("/twilio/outbound-call")
async def initiate_call(patient_id: str, session_id: str):
    """Twilio REST API call to initiate outbound call."""
    call = twilio_client.calls.create(
        to=patient.phone,
        from_=settings.TWILIO_PHONE_NUMBER,
        url=f"{settings.BASE_URL}/twilio/twiml?session_id={session_id}",
        status_callback=f"{settings.BASE_URL}/twilio/status",
        record=True,
        recording_status_callback=f"{settings.BASE_URL}/twilio/recording",
    )
    await OutreachSession.update(session_id, twilio_call_sid=call.sid)

@router.post("/twilio/twiml")
async def twiml_response(session_id: str):
    """TwiML that connects call to ConversationRelay WebSocket."""
    response = VoiceResponse()
    connect = Connect()
    # ConversationRelay handles STT/TTS; sends transcribed text to our WebSocket
    connect.conversation_relay(
        url=f"wss://{settings.DOMAIN}/twilio/ws/{session_id}",
        welcome_greeting="Hello, please hold for just a moment.",
        language="en-US",
        voice="en-US-Journey-F",  # Natural-sounding TTS voice
        transcription_provider="google",
    )
    response.append(connect)
    return Response(content=str(response), media_type="application/xml")

@router.websocket("/twilio/ws/{session_id}")
async def conversation_websocket(websocket: WebSocket, session_id: str):
    """WebSocket handler: receives patient speech, sends agent response."""
    await websocket.accept()
    session = await OutreachSession.get(session_id)
    discharge = await Discharge.get(session.discharge_id)
    patient = await Patient.get(session.patient_id)

    # Start Claude agent conversation in background
    agent_task = asyncio.create_task(
        run_conversation(session, discharge, patient, websocket)
    )

    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "prompt":
                # Patient speech transcribed by Twilio
                patient_text = data["voicePrompt"]
                await session.inject_patient_input(patient_text)
            elif data["type"] == "disconnect":
                agent_task.cancel()
                break
    except WebSocketDisconnect:
        agent_task.cancel()
```

### 2.4 Outreach Schedule

```python
# backend/tasks/outreach_scheduler.py
from celery import Celery

OUTREACH_SCHEDULE = {
    "high":   [24, 72, 168, 336, 720],   # Hours post-discharge: 1d, 3d, 7d, 14d, 30d
    "medium": [48, 168, 720],             # 2d, 7d, 30d
    "low":    [168, 720],                 # 7d, 30d
}

class OutreachScheduler:
    @staticmethod
    async def schedule(patient_id: str, risk_level: str, discharge_id: str):
        schedule_hours = OUTREACH_SCHEDULE[risk_level]
        for i, hours in enumerate(schedule_hours):
            eta = datetime.utcnow() + timedelta(hours=hours)
            initiate_outreach_call.apply_async(
                args=[patient_id, discharge_id, i + 1],
                eta=eta
            )
```

---

## Phase 3: Care Team Dashboard (Weeks 8–10)

**Goal:** Care coordinators have a real-time view of patient status, escalations, and conversation history.

### Key Dashboard Views

**1. Patient List (main view)**
- Table: Patient name, diagnosis, discharge date, risk level (color-coded badge), last contact, next scheduled call, escalation status
- Filters: risk level, condition type, escalation pending
- Real-time: escalation events appear without page refresh (WebSocket)

**2. Patient Detail**
- Full conversation transcript with timestamps
- Medication adherence summary (green/red per medication)
- Symptom log from all outreach sessions
- Escalation events with resolution status
- Upcoming scheduled calls

**3. Escalation Queue**
- Urgent escalations at top
- One-click: "Call patient now", "Resolved", "Assign to provider"
- Integration with Epic to create an in-basket message for the provider

**4. Analytics (Monthly)**
- 30-day readmission rate (before vs. after agent)
- Completed call rate, no-answer rate, patient satisfaction
- Top escalation reasons
- Medication adherence rates by condition
- Estimated cost savings (prevented readmissions × $15,200)

---

## Phase 4: Epic App Orchard Integration (Weeks 11–13)

**Goal:** Appear inside Epic's workflow so nurses can see agent status without leaving the EHR.

### Integration Points
1. **SMART on FHIR launch:** Embed dashboard as an iframe launchable from Epic's patient chart
2. **Epic In-Basket:** When agent escalates, create an Epic In-Basket message to the responsible provider via FHIR Task resource
3. **Epic Notifications:** Surface escalation as an Epic notification via FHIR Subscription

### App Orchard Submission Checklist
- [ ] FHIR R4 compliance validation
- [ ] HIPAA security assessment documentation
- [ ] Penetration test report (required by Epic)
- [ ] Clinical workflow documentation
- [ ] BAA templates ready for each health system customer
- [ ] Privacy policy and terms of service

---

## Phase 5: Compliance & Security (Ongoing)

| Requirement | Implementation |
|---|---|
| PHI encryption at rest | AWS KMS on all RDS, S3 |
| PHI encryption in transit | TLS 1.3 on all connections; Twilio media encrypted |
| Audit logging | CloudTrail + application-level audit for every PHI read/write |
| Access control | Role-based: care_coordinator, provider, admin; JWT with short expiry |
| BAA coverage | AWS BAA (self-service), Twilio BAA, Anthropic BAA |
| Call recordings | Stored in KMS-encrypted S3; access restricted to care_coordinator role |
| Data retention | Configurable per health system (default: 7 years per HIPAA) |
| Breach notification | CloudWatch alarm → SNS → compliance officer |
| PHI minimization | Never log PHI to stdout/CloudWatch logs; use patient_id references only |

---

## Monetization & Pricing

**Model:** SaaS, sold to hospital systems

| Tier | Price | Includes |
|---|---|---|
| Starter | $8/discharge | Up to 500 discharges/month; voice + SMS; standard protocols |
| Growth | $6/discharge | 500–2,000 discharges/month; custom protocols; Epic integration |
| Enterprise | Custom | >2,000/month; risk-sharing on readmission reduction; dedicated CSM |

**ROI pitch:** A 300-bed hospital with 15% readmission rate for CHF:
- ~120 CHF discharges/month × 15% = 18 readmissions/month
- Agent targets 25% reduction = 4–5 prevented readmissions/month
- Revenue preserved: 4.5 × $15,200 = **$68,400/month**
- Agent cost at Growth tier: 120 × $6 = **$720/month**
- **Net gain: ~$67,680/month; 94x ROI**

---

## Testing Strategy

### Unit Tests
- `test_fhir_parser.py` — mock FHIR responses, assert correct medication/diagnosis extraction
- `test_risk_scorer.py` — assert correct risk level for various patient profiles
- `test_escalation.py` — assert correct escalation level for each symptom/severity combo

### Integration Tests
- Epic FHIR sandbox (available at open.epic.com) for end-to-end discharge data pull
- Twilio test credentials for outbound call flow without spending credits

### Clinical Protocol Testing
- Script 20 synthetic patient conversations covering: normal check-in, medication non-adherence, urgent symptom (chest pain), missed follow-up appointment
- Verify Claude escalates correctly in all urgent scenarios
- Have a clinician review conversation transcripts for appropriateness

### Load Testing
- Simulate 100 concurrent WebSocket connections (Twilio calls)
- Verify SQS queue handles burst of 500 discharges in one hour

---

## Timeline Summary

| Phase | Weeks | Deliverable |
|---|---|---|
| 1. Foundation | 1–3 | HIPAA infra, FHIR integration, DB schema, risk scoring |
| 2. AI Agent Core | 4–7 | Claude agent, tool use, Twilio voice, outreach scheduler |
| 3. Dashboard | 8–10 | Care coordinator UI, escalation queue, analytics |
| 4. Epic Integration | 11–13 | SMART on FHIR launch, In-Basket alerts, App Orchard submission |
| 5. Pilot | 14–16 | Single health system pilot; 100 patients; measure readmission rate |
| 6. GA Launch | 17+ | Iterate on pilot learnings; expand to additional hospitals |

---

## Key Dependencies & Risks

| Risk | Mitigation |
|---|---|
| Epic FHIR access approval takes months | Start with Epic sandbox immediately; secure one health system champion early who can fast-track API access |
| Patients don't answer calls | Fall back to SMS; offer async voice message; track and report answer rates |
| Patients confuse AI for human | Agent introduces itself clearly: "This is an automated care check-in call from [Hospital]" |
| FDA regulation | Agent must not make specific treatment recommendations; always say "please contact your doctor" for clinical decisions |
| Twilio + Anthropic BAAs | Both have HIPAA BAA programs; initiate BAA request before any PHI flows through their services |
| Clinician skepticism | Loop in care coordinator as human-in-the-loop reviewer; no escalation goes without human confirmation |

---

*Sources: Epic FHIR R4 docs (open.epic.com), Twilio ConversationRelay docs, Anthropic Claude API docs, CMS HRRP (cms.gov), AWS HIPAA eligible services reference*

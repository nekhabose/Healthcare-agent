import asyncio
import sys
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

# Make `backend/` importable as the application root so absolute imports
# inside main.py (`from api.middleware...`) resolve when running tests.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from main import app                                # noqa: E402
from models.db import Discharge, Patient            # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_patient() -> Patient:
    p = Patient()
    p.id = uuid.uuid4()
    p.epic_patient_id = "epic-123"
    p.first_name_enc = "Jane"
    p.last_name_enc = "Smith"
    p.phone_enc = "+15551234567"
    p.date_of_birth = date(1950, 3, 15)
    p.risk_score = 70
    p.risk_level = "high"
    return p


@pytest.fixture
def sample_discharge(sample_patient) -> Discharge:
    d = Discharge()
    d.id = uuid.uuid4()
    d.patient_id = sample_patient.id
    d.discharge_date = date.today()
    d.hospital_name = "General Hospital"
    d.primary_diagnosis_code = "I50.9"
    d.primary_diagnosis_name = "Heart failure, unspecified"
    d.hrrp_condition = "heart_failure"
    d.medications = [
        {"name": "Furosemide", "dose": "40mg", "frequency": "daily"},
        {"name": "Lisinopril", "dose": "10mg", "frequency": "daily"},
        {"name": "Carvedilol", "dose": "6.25mg", "frequency": "twice daily"},
    ]
    d.followup_appointments = [
        {"specialty": "Cardiology", "scheduled_date": "2026-06-05"}
    ]
    d.instructions_summary = "Weigh yourself daily. Call if weight increases 2+ lbs."
    return d


@pytest.fixture
def mock_send_to_call():
    return AsyncMock()


@pytest.fixture
def mock_escalation_callback():
    return AsyncMock()

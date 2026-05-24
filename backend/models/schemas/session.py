import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class OutreachSessionCreate(BaseModel):
    patient_id: uuid.UUID
    discharge_id: uuid.UUID
    scheduled_at: datetime
    channel: str = "voice"
    outreach_number: int


class OutreachSessionRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    discharge_id: uuid.UUID
    scheduled_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    channel: str
    status: str
    outreach_number: int
    twilio_call_sid: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TurnCreate(BaseModel):
    session_id: uuid.UUID
    role: str
    content: str
    tool_calls: dict[str, Any] | None = None

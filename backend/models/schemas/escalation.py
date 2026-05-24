import uuid
from datetime import datetime

from pydantic import BaseModel


class EscalationCreate(BaseModel):
    session_id: uuid.UUID
    patient_id: uuid.UUID
    severity: str                    # urgent | high | medium
    reason: str
    symptoms_flagged: list[str] = []


class EscalationRead(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    patient_id: uuid.UUID
    severity: str
    reason: str
    symptoms_flagged: list[str]
    notified_at: datetime | None
    resolved_at: datetime | None
    resolved_by: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EscalationResolve(BaseModel):
    resolved_by: str

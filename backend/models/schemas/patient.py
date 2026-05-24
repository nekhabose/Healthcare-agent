import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    epic_patient_id: str
    mrn: str | None = None
    first_name: str
    last_name: str
    phone: str
    date_of_birth: date | None = None


class PatientUpdate(BaseModel):
    risk_score: int | None = None
    risk_level: str | None = None


class PatientRead(BaseModel):
    id: uuid.UUID
    epic_patient_id: str
    mrn: str | None
    first_name: str
    last_name: str
    phone: str
    date_of_birth: date | None
    risk_score: int | None
    risk_level: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

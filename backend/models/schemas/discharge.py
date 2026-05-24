import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class Medication(BaseModel):
    name: str
    dose: str | None = None
    frequency: str | None = None
    instructions: str | None = None
    rxcui: str | None = None


class FollowupAppointment(BaseModel):
    provider: str | None = None
    specialty: str | None = None
    scheduled_date: date | None = None
    location: str | None = None
    phone: str | None = None


class DischargeCreate(BaseModel):
    patient_id: uuid.UUID
    discharge_date: date
    hospital_name: str
    primary_diagnosis_code: str | None = None
    primary_diagnosis_name: str | None = None
    hrrp_condition: str | None = None
    discharge_summary_s3_key: str | None = None
    medications: list[dict[str, Any]] = []
    followup_appointments: list[dict[str, Any]] = []
    discharge_instructions: str | None = None
    instructions_summary: str | None = None


class DischargeRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    discharge_date: date
    hospital_name: str
    primary_diagnosis_code: str | None
    primary_diagnosis_name: str | None
    hrrp_condition: str | None
    medications: list[dict[str, Any]]
    followup_appointments: list[dict[str, Any]]
    discharge_instructions: str | None
    instructions_summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

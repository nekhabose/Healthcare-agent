"""Typed dataclasses for parsed FHIR discharge data."""
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class ParsedDischarge:
    epic_patient_id: str
    mrn: str | None
    first_name: str
    last_name: str
    phone: str
    date_of_birth: date | None
    age: int

    discharge_date: date
    primary_diagnosis_code: str | None
    primary_diagnosis_name: str | None
    hrrp_condition: str | None

    medications: list[dict[str, Any]] = field(default_factory=list)
    followup_appointments: list[dict[str, Any]] = field(default_factory=list)
    discharge_instructions: str | None = None
    instructions_summary: str | None = None

    prior_readmissions_90d: int = 0
    prior_ed_visits_90d: int = 0
    lives_alone: bool = False

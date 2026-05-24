"""
Dashboard API — endpoints for the care coordinator frontend.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from api.deps import (
    get_current_user,
    get_discharge_repo,
    get_escalation_repo,
    get_patient_repo,
    get_session_repo,
)
from models.schemas import EscalationRead, EscalationResolve, OutreachSessionRead, PatientRead
from repositories.discharge import DischargeRepository
from repositories.escalation import EscalationRepository
from repositories.patient import PatientRepository
from repositories.session import SessionRepository

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/patients", response_model=list[PatientRead])
async def list_patients(
    risk_level: str | None = None,
    limit: int = 100,
    offset: int = 0,
    patient_repo: PatientRepository = Depends(get_patient_repo),
    _user: dict = Depends(get_current_user),
):
    if risk_level:
        return await patient_repo.get_by_risk_level(risk_level)
    return await patient_repo.get_all(limit=limit, offset=offset)


@router.get("/patients/{patient_id}/sessions", response_model=list[OutreachSessionRead])
async def get_patient_sessions(
    patient_id: uuid.UUID,
    session_repo: SessionRepository = Depends(get_session_repo),
    _user: dict = Depends(get_current_user),
):
    return await session_repo.get_by_patient(patient_id)


@router.get("/escalations", response_model=list[EscalationRead])
async def list_escalations(
    unresolved_only: bool = True,
    escalation_repo: EscalationRepository = Depends(get_escalation_repo),
    _user: dict = Depends(get_current_user),
):
    if unresolved_only:
        return await escalation_repo.get_unresolved()
    return await escalation_repo.get_all()


@router.patch("/escalations/{escalation_id}/resolve", response_model=EscalationRead)
async def resolve_escalation(
    escalation_id: uuid.UUID,
    body: EscalationResolve,
    escalation_repo: EscalationRepository = Depends(get_escalation_repo),
    user: dict = Depends(get_current_user),
):
    escalation = await escalation_repo.get(escalation_id)
    return await escalation_repo.resolve(escalation, resolved_by=body.resolved_by or user.get("sub", "unknown"))


@router.get("/analytics/summary")
async def analytics_summary(
    patient_repo: PatientRepository = Depends(get_patient_repo),
    escalation_repo: EscalationRepository = Depends(get_escalation_repo),
    _user: dict = Depends(get_current_user),
):
    all_patients = await patient_repo.get_all(limit=10_000)
    high_risk = [p for p in all_patients if p.risk_level == "high"]
    open_escalations = await escalation_repo.get_unresolved()
    urgent = [e for e in open_escalations if e.severity == "urgent"]

    return {
        "total_patients": len(all_patients),
        "high_risk_patients": len(high_risk),
        "open_escalations": len(open_escalations),
        "urgent_escalations": len(urgent),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

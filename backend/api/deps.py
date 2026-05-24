"""
FastAPI dependency providers — single source of truth for DI.

Import these in routes; never construct services or clients in routes directly.
"""
from collections.abc import AsyncGenerator

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings, get_settings
from database import get_db
from fhir.client import EpicFHIRClient
from repositories.discharge import DischargeRepository
from repositories.escalation import EscalationRepository
from repositories.patient import PatientRepository
from repositories.session import SessionRepository, TurnRepository
from services.discharge import DischargeService
from services.notification import BaseNotifier, get_notifier
from services.outreach import OutreachService

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        payload = pyjwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_fhir_client() -> EpicFHIRClient:
    return EpicFHIRClient()


def get_notifier_dep() -> BaseNotifier:
    return get_notifier()


def get_patient_repo(db: AsyncSession = Depends(get_db)) -> PatientRepository:
    return PatientRepository(db)


def get_discharge_repo(db: AsyncSession = Depends(get_db)) -> DischargeRepository:
    return DischargeRepository(db)


def get_session_repo(db: AsyncSession = Depends(get_db)) -> SessionRepository:
    return SessionRepository(db)


def get_escalation_repo(db: AsyncSession = Depends(get_db)) -> EscalationRepository:
    return EscalationRepository(db)


def get_discharge_service(
    db: AsyncSession = Depends(get_db),
    fhir_client: EpicFHIRClient = Depends(get_fhir_client),
) -> DischargeService:
    return DischargeService(db, fhir_client)

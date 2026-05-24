"""
Outreach scheduling tasks — run via Celery + SQS.

Schedules the 5-touch outreach sequence based on risk level.
Each task initiates a Twilio outbound call at the right time.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from twilio.rest import Client

from config import get_settings
from database import AsyncSessionLocal
from repositories.patient import PatientRepository
from repositories.session import SessionRepository
from .celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

OUTREACH_HOURS: dict[str, list[int]] = {
    "high":   [24, 72, 168, 336, 720],
    "medium": [48, 168, 720],
    "low":    [168, 720],
}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def schedule_outreach_calls(self, patient_id: str, discharge_id: str) -> None:
    """Create OutreachSession records and queue individual call tasks."""
    try:
        asyncio.run(_schedule(patient_id, discharge_id))
    except Exception as exc:
        logger.exception("schedule_outreach_calls failed patient_id=%s", patient_id)
        raise self.retry(exc=exc)


async def _schedule(patient_id: str, discharge_id: str) -> None:
    async with AsyncSessionLocal() as db:
        patient = await PatientRepository(db).get(uuid.UUID(patient_id))
        session_repo = SessionRepository(db)
        risk_level = patient.risk_level or "medium"
        hours_list = OUTREACH_HOURS.get(risk_level, OUTREACH_HOURS["medium"])

        now = datetime.now(timezone.utc)
        for i, hours in enumerate(hours_list):
            eta = now + timedelta(hours=hours)
            session = await session_repo.create(
                patient_id=uuid.UUID(patient_id),
                discharge_id=uuid.UUID(discharge_id),
                scheduled_at=eta,
                channel="voice",
                outreach_number=i + 1,
            )
            initiate_call.apply_async(
                args=[str(session.id), patient_id, discharge_id],
                eta=eta,
            )
        await db.commit()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def initiate_call(self, session_id: str, patient_id: str, discharge_id: str) -> None:
    """Place the outbound Twilio call for one scheduled session."""
    try:
        asyncio.run(_initiate(session_id, patient_id))
    except Exception as exc:
        logger.exception("initiate_call failed session_id=%s", session_id)
        raise self.retry(exc=exc)


async def _initiate(session_id: str, patient_id: str) -> None:
    twilio = Client(settings.twilio_account_sid, settings.twilio_auth_token)

    async with AsyncSessionLocal() as db:
        patient = await PatientRepository(db).get(uuid.UUID(patient_id))
        # phone_enc is decrypted by application-layer encryption in production
        patient_phone = patient.phone_enc

    call = twilio.calls.create(
        to=patient_phone,
        from_=settings.twilio_phone_number,
        url=f"{settings.base_url}/twilio/twiml?session_id={session_id}",
        status_callback=f"{settings.base_url}/twilio/status",
        record=True,
    )
    logger.info("Call initiated session_id=%s twilio_sid=%s", session_id, call.sid)

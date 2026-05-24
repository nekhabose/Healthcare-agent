import uuid

from sqlalchemy import select

from models.db import ConversationTurn, OutreachSession
from .base import BaseRepository


class SessionRepository(BaseRepository[OutreachSession]):
    model = OutreachSession

    async def get_by_patient(self, patient_id: uuid.UUID) -> list[OutreachSession]:
        return await self.filter_by(patient_id=patient_id)

    async def get_pending(self) -> list[OutreachSession]:
        return await self.filter_by(status="scheduled")

    async def get_by_twilio_sid(self, call_sid: str) -> OutreachSession | None:
        return await self.first_by(twilio_call_sid=call_sid)


class TurnRepository(BaseRepository[ConversationTurn]):
    model = ConversationTurn

    async def get_by_session(self, session_id: uuid.UUID) -> list[ConversationTurn]:
        result = await self.db.execute(
            select(ConversationTurn)
            .where(ConversationTurn.session_id == session_id)
            .order_by(ConversationTurn.created_at)
        )
        return list(result.scalars().all())

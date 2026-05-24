import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from models.db import Escalation
from .base import BaseRepository


class EscalationRepository(BaseRepository[Escalation]):
    model = Escalation

    async def get_unresolved(self) -> list[Escalation]:
        result = await self.db.execute(
            select(Escalation)
            .where(Escalation.resolved_at.is_(None))
            .order_by(Escalation.severity, Escalation.created_at)
        )
        return list(result.scalars().all())

    async def get_by_patient(self, patient_id: uuid.UUID) -> list[Escalation]:
        return await self.filter_by(patient_id=patient_id)

    async def resolve(self, escalation: Escalation, resolved_by: str) -> Escalation:
        return await self.update(
            escalation,
            resolved_at=datetime.now(timezone.utc),
            resolved_by=resolved_by,
        )

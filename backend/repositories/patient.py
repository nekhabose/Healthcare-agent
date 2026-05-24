from sqlalchemy import select

from models.db import Patient
from .base import BaseRepository


class PatientRepository(BaseRepository[Patient]):
    model = Patient

    async def get_by_epic_id(self, epic_patient_id: str) -> Patient | None:
        result = await self.db.execute(
            select(Patient).where(Patient.epic_patient_id == epic_patient_id)
        )
        return result.scalar_one_or_none()

    async def get_by_risk_level(self, risk_level: str) -> list[Patient]:
        return await self.filter_by(risk_level=risk_level)

import uuid

from sqlalchemy import select

from models.db import Discharge
from .base import BaseRepository


class DischargeRepository(BaseRepository[Discharge]):
    model = Discharge

    async def get_by_patient(self, patient_id: uuid.UUID) -> list[Discharge]:
        return await self.filter_by(patient_id=patient_id)

    async def get_latest_for_patient(self, patient_id: uuid.UUID) -> Discharge | None:
        result = await self.db.execute(
            select(Discharge)
            .where(Discharge.patient_id == patient_id)
            .order_by(Discharge.discharge_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_hrrp_condition(self, condition: str) -> list[Discharge]:
        return await self.filter_by(hrrp_condition=condition)

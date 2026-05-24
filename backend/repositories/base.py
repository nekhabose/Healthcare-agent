"""
Generic async repository.

All concrete repositories inherit BaseRepository[M] and get standard CRUD
for free. Specialised queries live in the subclass only.
"""
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Base

M = TypeVar("M", bound=Base)


class BaseRepository(Generic[M]):
    model: type[M]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, id: UUID) -> M | None:
        return await self.db.get(self.model, id)

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[M]:
        result = await self.db.execute(select(self.model).limit(limit).offset(offset))
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> M:
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(self, instance: M, **kwargs: Any) -> M:
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: M) -> None:
        await self.db.delete(instance)
        await self.db.flush()

    async def filter_by(self, **kwargs: Any) -> list[M]:
        conditions = [getattr(self.model, k) == v for k, v in kwargs.items()]
        result = await self.db.execute(select(self.model).where(*conditions))
        return list(result.scalars().all())

    async def first_by(self, **kwargs: Any) -> M | None:
        results = await self.filter_by(**kwargs)
        return results[0] if results else None

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import BaseModel


class BaseRepository[ModelType: BaseModel]:
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def _get(self, id: int) -> ModelType | None:
        return await self.session.get(self.model, id)

    async def _create(self, **kwargs: Any) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def _delete(self, id: int) -> bool:
        instance = await self._get(id)

        if instance is not None:
            await self.session.delete(instance)
            await self.session.flush()

        return bool(instance)

    async def _list(self) -> list[ModelType]:
        result = await self.session.execute(select(self.model))
        return list(result.scalars().all())

    async def _update(self, id: int, updates: dict) -> ModelType | None:
        instance = await self._get(id)

        if instance is None:
            return None

        for key, value in updates.items():
            setattr(instance, key, value)

        await self.session.flush()

        return instance

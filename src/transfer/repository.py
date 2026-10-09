import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.base_repo import BaseRepository
from src.transfer.models import Transfer, TransferStatus


class TransferRepository(BaseRepository[Transfer]):
    def __init__(self, session: AsyncSession):
        super().__init__(Transfer, session)

    async def get(self, id: uuid.UUID) -> Transfer | None:
        return await self.session.get(Transfer, id)

    async def get_by_external_id(self, external_id: str) -> Transfer | None:
        result = await self.session.execute(
            select(Transfer).where(Transfer.external_id == external_id)
        )
        return result.scalars().one_or_none()

    async def create(
        self,
        *,
        external_id: str,
        currency: str,
        amount: Decimal,
        destination: str,
        comment: str | None,
        status: TransferStatus = TransferStatus.PENDING,
        tx_hash: str | None = None,
    ) -> Transfer:
        return await self._create(
            external_id=external_id,
            currency=currency,
            amount=amount,
            destination=destination,
            comment=comment,
            status=status,
            tx_hash=tx_hash,
        )

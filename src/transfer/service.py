import asyncio
import hashlib
import hmac
import json
import secrets
from decimal import Decimal

import httpx
import structlog
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from config.settings import Settings
from src.transfer.models import Transfer, TransferStatus
from src.transfer.repository import TransferRepository

log = structlog.get_logger()


def generate_signature(api_key: str, body: bytes) -> str:
    token_hash = hashlib.sha256(api_key.encode()).digest()
    return hmac.new(token_hash, body, hashlib.sha256).hexdigest()


def format_amount(amount: Decimal) -> str:
    return f"{amount.normalize():f}"


class TransferService:
    def __init__(self, repo: TransferRepository, settings: Settings):
        self.repo = repo
        self.settings = settings

    async def create_idempotent(
        self,
        *,
        external_id: str,
        currency: str,
        amount: Decimal,
        destination: str,
        comment: str | None,
    ) -> tuple[Transfer, bool]:
        existing = await self.repo.get_by_external_id(external_id)
        if existing is not None:
            return existing, False

        try:
            transfer = await self.repo.create(
                external_id=external_id,
                currency=currency,
                amount=amount,
                destination=destination,
                comment=comment,
                status=TransferStatus.PENDING,
            )
            await self.repo.session.flush()
        except IntegrityError:
            await self.repo.session.rollback()
            existing = await self.repo.get_by_external_id(external_id)
            if existing is None:
                raise
            return existing, False

        transfer = await self._execute(transfer)
        await self.repo.session.commit()
        await self.repo.session.refresh(transfer)

        await self._notify(transfer)

        return transfer, True

    async def _execute(self, transfer: Transfer) -> Transfer:
        try:
            transfer.tx_hash = secrets.token_hex(32)
            transfer.status = TransferStatus.COMPLETED
            await self.repo.session.flush()
        except SQLAlchemyError:
            log.exception("transfer execution failed", external_id=transfer.external_id)
            transfer.tx_hash = None
            transfer.status = TransferStatus.FAILED
            await self.repo.session.flush()
        return transfer

    def build_webhook_body(self, transfer: Transfer) -> bytes:
        payload = {
            "id": str(transfer.id),
            "external_id": transfer.external_id,
            "amount": format_amount(transfer.amount),
            "status": transfer.status.value,
            "details": {
                "from_address": self.settings.from_address,
                "to_address": transfer.destination,
                "tx_hash": transfer.tx_hash,
            },
        }
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()

    async def _notify(self, transfer: Transfer) -> None:
        if transfer.status not in (TransferStatus.COMPLETED, TransferStatus.FAILED):
            return

        body = self.build_webhook_body(transfer)
        signature = generate_signature(
            self.settings.webhook.api_key.get_secret_value(), body
        )
        headers = {
            self.settings.webhook.signature_header: signature,
            "Content-Type": "application/json",
        }
        url = str(self.settings.webhook.url)
        timeout = self.settings.webhook.timeout_sec
        max_retries = self.settings.webhook.max_retries

        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(max_retries + 1):
                try:
                    response = await client.post(url, content=body, headers=headers)
                    response.raise_for_status()
                    log.info(
                        "webhook delivered",
                        transfer_id=str(transfer.id),
                        attempt=attempt,
                    )
                    return
                except httpx.HTTPError as exc:
                    log.warning(
                        "webhook delivery failed",
                        transfer_id=str(transfer.id),
                        attempt=attempt,
                        error=str(exc),
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(min(0.5 * (2**attempt), 10.0))

        log.error("webhook delivery exhausted", transfer_id=str(transfer.id))

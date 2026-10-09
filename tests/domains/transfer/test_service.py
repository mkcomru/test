import json
import uuid
from decimal import Decimal

import httpx

from src.transfer.models import Transfer, TransferStatus
from src.transfer.service import TransferService, generate_signature


def _payload(**overrides) -> dict:
    base = {
        "external_id": "ext-1",
        "currency": "USDT",
        "amount": Decimal("25.500"),
        "destination": "external-addr",
        "comment": None,
    }
    base.update(overrides)
    return base


async def test_create_returns_completed_and_sends_signed_webhook(
    service: TransferService, webhook_capture: dict
) -> None:
    transfer, created = await service.create_idempotent(**_payload())

    assert created is True
    assert transfer.status == TransferStatus.COMPLETED
    assert transfer.tx_hash is not None
    assert len(transfer.tx_hash) == 64

    calls = webhook_capture["calls"]
    assert len(calls) == 1
    headers = calls[0]["headers"]
    body = calls[0]["content"]
    assert isinstance(body, bytes)

    signature_header = service.settings.webhook.signature_header
    assert headers[signature_header] == generate_signature(
        service.settings.webhook.api_key.get_secret_value(), body
    )

    data = json.loads(body)
    assert data == {
        "id": str(transfer.id),
        "external_id": "ext-1",
        "amount": "25.5",
        "status": "completed",
        "details": {
            "from_address": service.settings.from_address,
            "to_address": "external-addr",
            "tx_hash": transfer.tx_hash,
        },
    }


async def test_repeat_returns_first_record_without_new_webhook(
    service: TransferService, webhook_capture: dict
) -> None:
    first, created_first = await service.create_idempotent(**_payload())
    second, created_second = await service.create_idempotent(**_payload())

    assert created_first is True
    assert created_second is False
    assert second.id == first.id
    assert len(webhook_capture["calls"]) == 1


async def test_repeat_with_different_payload_keeps_first_record(
    service: TransferService, webhook_capture: dict
) -> None:
    first, _ = await service.create_idempotent(**_payload())
    second, created = await service.create_idempotent(
        **_payload(amount=Decimal("999"), currency="BTC", destination="other")
    )

    assert created is False
    assert second.id == first.id
    assert second.amount == Decimal("25.500")
    assert second.currency == "USDT"
    assert second.destination == "external-addr"


async def test_webhook_retried_then_succeeds(
    service: TransferService, webhook_capture: dict, no_sleep: None
) -> None:
    webhook_capture["script"].append(500)
    webhook_capture["script"].append(200)

    transfer, created = await service.create_idempotent(**_payload())

    assert created is True
    assert transfer.status == TransferStatus.COMPLETED
    assert len(webhook_capture["calls"]) == 2


async def test_webhook_failure_does_not_fail_transfer(
    service: TransferService, webhook_capture: dict, no_sleep: None
) -> None:
    webhook_capture["script"].extend(
        [httpx.ConnectError("down")] * (service.settings.webhook.max_retries + 1)
    )

    transfer, created = await service.create_idempotent(**_payload())

    assert created is True
    assert transfer.status == TransferStatus.COMPLETED
    assert len(webhook_capture["calls"]) == service.settings.webhook.max_retries + 1


async def test_notify_skips_pending_transfers(
    service: TransferService, webhook_capture: dict
) -> None:
    pending = Transfer(
        id=uuid.uuid4(),
        external_id="ext-pending",
        currency="USDT",
        amount=Decimal("1"),
        destination="addr",
        comment=None,
        status=TransferStatus.PENDING,
        tx_hash=None,
    )

    await service._notify(pending)

    assert webhook_capture["calls"] == []

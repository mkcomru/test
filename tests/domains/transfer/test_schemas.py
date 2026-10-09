import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.transfer.schemas import (
    TransferCreate,
    TransferOut,
    WebhookDetails,
    WebhookPayload,
    WebhookStatus,
)


def test_create_accepts_decimal_string() -> None:
    payload = TransferCreate(
        external_id="ext-1", currency="USDT", amount="10.5000", destination="addr-1"
    )
    assert payload.amount == Decimal("10.5000")
    assert payload.comment is None


def test_create_accepts_comment() -> None:
    payload = TransferCreate(
        external_id="ext-1",
        currency="USDT",
        amount="1",
        destination="addr-1",
        comment="hello",
    )
    assert payload.comment == "hello"


@pytest.mark.parametrize("bad_amount", ["0", "-5", "NaN", "Infinity", "-Infinity"])
def test_create_rejects_non_positive_or_special_amounts(bad_amount: str) -> None:
    with pytest.raises(ValidationError):
        TransferCreate(
            external_id="ext-1",
            currency="USDT",
            amount=bad_amount,
            destination="addr-1",
        )


def test_create_rejects_empty_external_id() -> None:
    with pytest.raises(ValidationError):
        TransferCreate(
            external_id="", currency="USDT", amount="1", destination="addr-1"
        )


def test_create_rejects_too_long_external_id() -> None:
    with pytest.raises(ValidationError):
        TransferCreate(
            external_id="x" * 129, currency="USDT", amount="1", destination="addr-1"
        )


def test_out_serializes_amount_as_string() -> None:
    out = TransferOut(
        id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        external_id="ext-1",
        currency="USDT",
        amount=Decimal("10.5000"),
        destination="addr-1",
        status="completed",
    )
    dumped = out.model_dump(mode="json")
    assert dumped["amount"] == "10.5"
    assert dumped["status"] == "completed"
    assert dumped["id"] == "12345678-1234-5678-1234-567812345678"


def test_webhook_payload_shape() -> None:
    payload = WebhookPayload(
        id=uuid.uuid4(),
        external_id="ext-1",
        amount=Decimal("3.140"),
        status=WebhookStatus.COMPLETED,
        details=WebhookDetails(
            from_address="internal", to_address="external", tx_hash="0xabc"
        ),
    )
    dumped = payload.model_dump(mode="json")
    assert dumped["amount"] == "3.14"
    assert dumped["details"] == {
        "from_address": "internal",
        "to_address": "external",
        "tx_hash": "0xabc",
    }


def test_webhook_payload_rejects_pending_status() -> None:
    with pytest.raises(ValidationError):
        WebhookPayload(
            id=uuid.uuid4(),
            external_id="ext-1",
            amount=Decimal("1"),
            status="pending",
            details=WebhookDetails(from_address="a", to_address="b"),
        )

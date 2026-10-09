import uuid
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from config.settings import get_settings
from src.transfer.dependencies import get_transfer_service
from src.transfer.models import Transfer, TransferStatus
from src.transfer.routers import router


class StubService:
    def __init__(self, created: bool):
        transfer = Transfer(
            id=uuid.uuid4(),
            external_id="ext-1",
            currency="USDT",
            amount=Decimal("10.5"),
            destination="external-addr",
            comment=None,
            status=TransferStatus.COMPLETED,
            tx_hash="ab" * 32,
        )
        self._result = (transfer, created)

    async def create_idempotent(self, **kwargs):
        return self._result


def _client(created: bool) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_transfer_service] = lambda: StubService(created)
    return TestClient(app, raise_server_exceptions=False)


def _payload() -> dict:
    return {
        "external_id": "ext-1",
        "currency": "USDT",
        "amount": "10.5",
        "destination": "external-addr",
    }


def _auth_headers() -> dict:
    token = get_settings().api_token.get_secret_value()
    return {"Authorization": f"Bearer {token}"}


def test_post_without_token_is_unauthorized() -> None:
    response = _client(created=True).post("/api/v1/transfer", json=_payload())
    assert response.status_code == 401


def test_post_with_wrong_token_is_unauthorized() -> None:
    response = _client(created=True).post(
        "/api/v1/transfer",
        json=_payload(),
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


def test_post_first_time_returns_201() -> None:
    response = _client(created=True).post(
        "/api/v1/transfer", json=_payload(), headers=_auth_headers()
    )
    assert response.status_code == 201
    data = response.json()
    assert data["external_id"] == "ext-1"
    assert data["currency"] == "USDT"
    assert data["amount"] == "10.5"
    assert data["destination"] == "external-addr"
    assert data["status"] == "completed"
    uuid.UUID(data["id"])


def test_post_repeat_returns_200() -> None:
    response = _client(created=False).post(
        "/api/v1/transfer", json=_payload(), headers=_auth_headers()
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_post_invalid_amount_returns_422() -> None:
    payload = _payload()
    payload["amount"] = "0"
    response = _client(created=True).post(
        "/api/v1/transfer", json=payload, headers=_auth_headers()
    )
    assert response.status_code == 422

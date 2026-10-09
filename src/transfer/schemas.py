import enum
import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from src.transfer.models import TransferStatus

DecimalAsString = Annotated[
    Decimal,
    PlainSerializer(lambda v: f"{v.normalize():f}", return_type=str),
]


class TransferCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    external_id: str = Field(min_length=1, max_length=128)
    currency: str = Field(min_length=1, max_length=16)
    amount: Decimal = Field(gt=0, allow_inf_nan=False, max_digits=36, decimal_places=18)
    destination: str = Field(min_length=1, max_length=1024)
    comment: str | None = Field(default=None, max_length=2048)


class TransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    external_id: str
    currency: str
    amount: DecimalAsString
    destination: str
    status: TransferStatus


class WebhookStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class WebhookDetails(BaseModel):
    from_address: str
    to_address: str
    tx_hash: str | None = None


class WebhookPayload(BaseModel):
    id: uuid.UUID
    external_id: str
    amount: DecimalAsString
    status: WebhookStatus
    details: WebhookDetails

from fastapi import APIRouter, Depends, Response, status

from src.transfer.dependencies import TransferServiceDep, verify_token
from src.transfer.schemas import TransferCreate, TransferOut

router = APIRouter(prefix="/api/v1/transfer", tags=["transfer"])


@router.post(
    "",
    response_model=TransferOut,
    dependencies=[Depends(verify_token)],
)
async def create_transfer(
    payload: TransferCreate, service: TransferServiceDep, response: Response
) -> TransferOut:
    transfer, created = await service.create_idempotent(
        external_id=payload.external_id,
        currency=payload.currency,
        amount=payload.amount,
        destination=payload.destination,
        comment=payload.comment,
    )
    response.status_code = (
        status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )
    return TransferOut.model_validate(transfer)

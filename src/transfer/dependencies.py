import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings, get_settings
from src.common.database import get_db
from src.transfer.repository import TransferRepository
from src.transfer.service import TransferService

SessionDep = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

bearer_scheme = HTTPBearer(auto_error=False)


async def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: SettingsDep,
) -> None:
    token = credentials.credentials if credentials is not None else ""
    if not secrets.compare_digest(token, settings.api_token.get_secret_value()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_transfer_repository(session: SessionDep) -> TransferRepository:
    return TransferRepository(session)


def get_transfer_service(
    repo: Annotated[TransferRepository, Depends(get_transfer_repository)],
    settings: SettingsDep,
) -> TransferService:
    return TransferService(repo, settings)


TransferServiceDep = Annotated[TransferService, Depends(get_transfer_service)]

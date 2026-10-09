from typing import Annotated

from fastapi import Depends

from src.modules.common.email import EmailService
from src.modules.common.settings import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_email_service(settings: SettingsDep) -> EmailService:
    return EmailService(settings)


EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]

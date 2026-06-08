import pyotp
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError
from app.modules.auth.models import User


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=1)


class MfaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def setup(self, user: User) -> dict:
        if user.mfa_enabled:
            raise AppError("MFA already enabled.", 409)
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        await self.db.commit()
        uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=settings.APP_NAME)
        return {"secret": secret, "otpauth_uri": uri}

    async def enable(self, user: User, code: str) -> None:
        if user.mfa_enabled:
            raise AppError("MFA already enabled.", 409)
        if not user.mfa_secret or not verify_totp(user.mfa_secret, code):
            raise AppError("Invalid MFA code.", 400)
        user.mfa_enabled = True
        await self.db.commit()

    async def disable(self, user: User, code: str) -> None:
        if not user.mfa_enabled or not user.mfa_secret:
            raise AppError("MFA is not enabled.", 409)
        if not verify_totp(user.mfa_secret, code):
            raise AppError("Invalid MFA code.", 400)
        user.mfa_enabled = False
        user.mfa_secret = None
        await self.db.commit()

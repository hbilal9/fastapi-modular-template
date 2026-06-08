from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.exceptions import AppError
from app.modules.auth.models import AccountStatus, RefreshToken, User

MAX_FAILED_ATTEMPTS = 5


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, email: str, password: str, first_name: str, last_name: str) -> User:
        email = email.lower()
        if await self._get_by_email(email):
            raise AppError("Email already registered.", 409)
        user = User(
            email=email,
            password_hash=await security.hash_password(password),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
        )
        self.db.add(user)
        await self.db.commit()
        return user

    async def login(self, email: str, password: str) -> tuple[str, str]:
        user = await self._get_by_email(email.lower())
        if not user:
            await security.hash_password(password)
            raise AppError("Invalid credentials.", 401)
        if user.account_status == AccountStatus.LOCKED:
            raise AppError("Account is locked.", 423)
        if not await security.verify_password(password, user.password_hash):
            await self._register_failure(user)
            raise AppError("Invalid credentials.", 401)
        await self._register_success(user)
        return await self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        if not security.decode_token(refresh_token, "refresh"):
            raise AppError("Invalid refresh token.", 401)
        stored = await self._get_refresh(security.hash_token(refresh_token))
        if not stored or stored.revoked or stored.expires_at < datetime.now(UTC):
            raise AppError("Invalid refresh token.", 401)
        stored.revoked = True
        user = await self.db.get(User, stored.user_id)
        if not user:
            raise AppError("Invalid refresh token.", 401)
        return await self._issue_tokens(user)

    async def logout(self, refresh_token: str) -> None:
        stored = await self._get_refresh(security.hash_token(refresh_token))
        if stored:
            stored.revoked = True
            await self.db.commit()

    async def _issue_tokens(self, user: User) -> tuple[str, str]:
        access = security.create_access_token(str(user.id), {"role": user.role})
        refresh = security.create_refresh_token(str(user.id))
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=security.hash_token(refresh),
                expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )
        )
        await self.db.commit()
        return access, refresh

    async def _register_failure(self, user: User) -> None:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.account_status = AccountStatus.LOCKED
            user.locked_at = datetime.now(UTC)
            user.locked_reason = "Exceeded maximum failed login attempts."
        await self.db.commit()

    async def _register_success(self, user: User) -> None:
        user.failed_login_attempts = 0
        user.last_login_at = datetime.now(UTC)
        await self.db.commit()

    async def _get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def _get_refresh(self, token_hash: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

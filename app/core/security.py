import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import anyio.to_thread
import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


async def hash_password(password: str) -> str:
    return await anyio.to_thread.run_sync(_hash, password)


async def verify_password(password: str, password_hash: str) -> bool:
    return await anyio.to_thread.run_sync(_verify, password, password_hash)


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(subject: str, claims: dict | None = None) -> str:
    return _encode(subject, "access", timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), claims)


def create_refresh_token(subject: str, claims: dict | None = None) -> str:
    return _encode(subject, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), claims)


def create_mfa_token(subject: str) -> str:
    return _encode(subject, "mfa", timedelta(minutes=5), None)


def create_verification_token(subject: str) -> str:
    return _encode(subject, "verify", timedelta(hours=24), None)


def _encode(subject: str, token_type: str, expires_in: timedelta, claims: dict | None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_in,
        "jti": str(uuid.uuid4()),
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str, expected_type: str | None = None) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
    if expected_type and payload.get("type") != expected_type:
        return None
    return payload

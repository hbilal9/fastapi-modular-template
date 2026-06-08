from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.modules.auth.mfa import MfaService
from app.modules.auth.schema import (
    LoginRequest,
    MfaCodeRequest,
    MfaVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.modules.auth.service import AuthService
from app.shared.rate_limiter import EmailRateLimit, LoginRateLimit
from app.shared.response import success

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: DbSession):
    user = await AuthService(db).register(**data.model_dump())
    return success(UserResponse.model_validate(user).model_dump(mode="json"), "created")


@router.post("/login", dependencies=[LoginRateLimit])
async def login(data: LoginRequest, db: DbSession):
    return success(await AuthService(db).login(data.email, data.password))


@router.post("/verify-mfa-login")
async def verify_mfa_login(data: MfaVerifyRequest, db: DbSession):
    return success(await AuthService(db).verify_mfa_login(data.login_token, data.mfa_code))


@router.post("/verify-email")
async def verify_email(data: VerifyEmailRequest, db: DbSession):
    await AuthService(db).verify_email(data.token)
    return success(status="verified")


@router.post("/resend-verification", dependencies=[EmailRateLimit])
async def resend_verification(data: ResendVerificationRequest, db: DbSession):
    await AuthService(db).resend_verification(data.email)
    return success(status="sent")


@router.post("/refresh")
async def refresh(data: RefreshRequest, db: DbSession):
    access, refresh = await AuthService(db).refresh(data.refresh_token)
    tokens = TokenResponse(access_token=access, refresh_token=refresh)
    return success(tokens.model_dump())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest, db: DbSession):
    await AuthService(db).logout(data.refresh_token)


@router.get("/me")
async def me(user: CurrentUser):
    return success(UserResponse.model_validate(user).model_dump(mode="json"))


@router.post("/mfa/setup")
async def mfa_setup(user: CurrentUser, db: DbSession):
    return success(await MfaService(db).setup(user))


@router.post("/mfa/enable")
async def mfa_enable(data: MfaCodeRequest, user: CurrentUser, db: DbSession):
    await MfaService(db).enable(user, data.mfa_code)
    return success(status="enabled")


@router.post("/mfa/disable")
async def mfa_disable(data: MfaCodeRequest, user: CurrentUser, db: DbSession):
    await MfaService(db).disable(user, data.mfa_code)
    return success(status="disabled")

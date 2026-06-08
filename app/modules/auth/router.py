from fastapi import APIRouter, Depends, status

from app.core.dependencies import CurrentUser, DbSession
from app.modules.auth.schema import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService
from app.shared.rate_limiter import rate_limit
from app.shared.response import success

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: DbSession):
    user = await AuthService(db).register(**data.model_dump())
    return success(UserResponse.model_validate(user).model_dump(mode="json"), "created")


@router.post("/login", dependencies=[Depends(rate_limit(5, 60))])
async def login(data: LoginRequest, db: DbSession):
    access, refresh = await AuthService(db).login(data.email, data.password)
    tokens = TokenResponse(access_token=access, refresh_token=refresh)
    return success(tokens.model_dump())


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

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.modules.auth.schema import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: DbSession):
    user = await AuthService(db).register(**data.model_dump())
    return {"data": UserResponse.model_validate(user).model_dump(mode="json"), "status": "created"}


@router.post("/login")
async def login(data: LoginRequest, db: DbSession):
    access, refresh = await AuthService(db).login(data.email, data.password)
    tokens = TokenResponse(access_token=access, refresh_token=refresh)
    return {"data": tokens.model_dump(), "status": "ok"}


@router.post("/refresh")
async def refresh(data: RefreshRequest, db: DbSession):
    access, refresh = await AuthService(db).refresh(data.refresh_token)
    tokens = TokenResponse(access_token=access, refresh_token=refresh)
    return {"data": tokens.model_dump(), "status": "ok"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest, db: DbSession):
    await AuthService(db).logout(data.refresh_token)


@router.get("/me")
async def me(user: CurrentUser):
    return {"data": UserResponse.model_validate(user).model_dump(mode="json"), "status": "ok"}

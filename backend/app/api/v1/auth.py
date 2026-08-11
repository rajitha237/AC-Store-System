from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser, DatabaseSession
from app.core.config import get_settings
from app.core.security import create_access_token
from app.schemas.auth import TokenResponse, UserResponse
from app.services.auth import authenticate_user

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

settings = get_settings()


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    form_data: Annotated[
        OAuth2PasswordRequestForm,
        Depends(),
    ],
    session: DatabaseSession,
) -> TokenResponse:
    user = await authenticate_user(
        session=session,
        login=form_data.username,
        password=form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username, email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "username": user.username,
            "role": user.role,
        },
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
async def read_current_user(
    current_user: CurrentUser,
) -> UserResponse:
    return UserResponse.model_validate(current_user)

import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import TokenResponse, UserResponse
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    delete_refresh_token,
    exchange_github_code,
    get_github_auth_url,
    get_github_user,
    save_refresh_token,
    upsert_user,
    validate_refresh_token,
)
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/github")
async def github_login():
    state = secrets.token_urlsafe(16)
    url = get_github_auth_url(state)
    return RedirectResponse(url=url)


@router.get("/github/callback")
async def github_callback(
    code: str,
    state: str | None = None,
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    # Exchange code for GitHub access token
    token_data = await exchange_github_code(code)

    github_access_token = token_data.get("access_token")
    if not github_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to obtain GitHub access token",
        )

    # Get GitHub user info
    github_user = await get_github_user(github_access_token)

    # Upsert user in our DB
    user = await upsert_user(db, github_user)

    # Create JWT and refresh token
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token()
    await save_refresh_token(db, user.id, refresh_token)

    # Redirect to frontend with access token; set refresh token as httpOnly cookie
    redirect_response = RedirectResponse(
        url=f"{settings.frontend_url}/auth/callback?token={access_token}"
    )
    redirect_response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True in production with HTTPS
        max_age=settings.refresh_token_expire_days * 86400,
    )
    return redirect_response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )

    token_record = await validate_refresh_token(db, refresh_token)
    if token_record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token = create_access_token(str(token_record.user_id))
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        await delete_refresh_token(db, refresh_token)

    response.delete_cookie(key="refresh_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

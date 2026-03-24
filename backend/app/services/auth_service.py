import secrets
from datetime import datetime, timedelta, timezone

import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import RefreshToken, User


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token() -> str:
    return secrets.token_hex(32)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None


def get_github_auth_url(state: str) -> str:
    params = (
        f"client_id={settings.github_client_id}"
        f"&scope=read:user,user:email"
        f"&state={state}"
    )
    return f"https://github.com/login/oauth/authorize?{params}"


async def exchange_github_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()


async def get_github_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        return response.json()


async def upsert_user(db: AsyncSession, github_user: dict) -> User:
    result = await db.execute(select(User).where(User.github_id == github_user["id"]))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            github_id=github_user["id"],
            github_username=github_user.get("login", ""),
            name=github_user.get("name") or github_user.get("login", ""),
            email=github_user.get("email"),
            avatar_url=github_user.get("avatar_url"),
        )
        db.add(user)
    else:
        user.github_username = github_user.get("login", user.github_username)
        user.name = github_user.get("name") or github_user.get("login", user.name)
        user.email = github_user.get("email", user.email)
        user.avatar_url = github_user.get("avatar_url", user.avatar_url)

    await db.commit()
    await db.refresh(user)
    return user


async def save_refresh_token(db: AsyncSession, user_id, token: str) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
    )
    db.add(refresh_token)
    await db.commit()


async def validate_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
    refresh_token = result.scalar_one_or_none()

    if refresh_token is None:
        return None

    if refresh_token.expires_at < datetime.now(timezone.utc):
        await db.delete(refresh_token)
        await db.commit()
        return None

    return refresh_token


async def delete_refresh_token(db: AsyncSession, token: str) -> None:
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
    refresh_token = result.scalar_one_or_none()
    if refresh_token:
        await db.delete(refresh_token)
        await db.commit()


async def delete_user_refresh_tokens(db: AsyncSession, user_id) -> None:
    result = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id))
    tokens = result.scalars().all()
    for token in tokens:
        await db.delete(token)
    await db.commit()

"""Claude OAuth credentials management with DB persistence.

On startup: load from DB (or env var as fallback) → write to disk.
After SDK calls: read from disk → if changed, save back to DB.
"""
import json
import logging
import os
import time

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig

logger = logging.getLogger(__name__)

CREDENTIALS_PATH = os.path.expanduser("~/.claude/.credentials.json")
REFRESH_ENDPOINT = "https://api.anthropic.com/v1/oauth/token"
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
DB_KEY = "claude_credentials"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def load_credentials_from_db(db: AsyncSession) -> dict | None:
    """Load credentials JSON from DB."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == DB_KEY))
    row = result.scalar_one_or_none()
    if row:
        try:
            return json.loads(row.value)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in DB credentials")
    return None


async def save_credentials_to_db(db: AsyncSession, creds: dict) -> None:
    """Save credentials JSON to DB (upsert)."""
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == DB_KEY))
    row = result.scalar_one_or_none()
    value = json.dumps(creds)
    if row:
        row.value = value
    else:
        db.add(SystemConfig(key=DB_KEY, value=value))
    await db.commit()
    logger.warning("Credentials saved to DB")


# ---------------------------------------------------------------------------
# Disk helpers
# ---------------------------------------------------------------------------

def _read_disk() -> dict | None:
    if not os.path.exists(CREDENTIALS_PATH):
        return None
    try:
        with open(CREDENTIALS_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_disk(creds: dict) -> None:
    os.makedirs(os.path.dirname(CREDENTIALS_PATH), exist_ok=True)
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(creds, f)
    os.chmod(CREDENTIALS_PATH, 0o600)


# ---------------------------------------------------------------------------
# Startup: load credentials to disk
# ---------------------------------------------------------------------------

async def init_credentials(db: AsyncSession) -> bool:
    """Load credentials: compare DB and env var, use whichever is newer.

    Call this once at startup or before first SDK call.
    Returns True if credentials are available.
    """
    def _exp(c: dict | None) -> int:
        return (c or {}).get("claudeAiOauth", {}).get("expiresAt", 0)

    db_creds = await load_credentials_from_db(db)
    env_creds = None
    env_raw = os.environ.get("CLAUDE_CREDENTIALS")
    if env_raw:
        try:
            env_creds = json.loads(env_raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in CLAUDE_CREDENTIALS env var")

    db_exp = _exp(db_creds)
    env_exp = _exp(env_creds)

    if db_creds and db_exp >= env_exp:
        logger.warning("Using credentials from DB (expiresAt=%s)", db_exp)
        _write_disk(db_creds)
        return True

    if env_creds:
        logger.warning("Using credentials from env var (expiresAt=%s, DB expiresAt=%s)", env_exp, db_exp or "none")
        _write_disk(env_creds)
        await save_credentials_to_db(db, env_creds)
        return True

    logger.warning("No credentials found in DB or env var")
    return False


# ---------------------------------------------------------------------------
# Post-call: sync disk → DB if changed
# ---------------------------------------------------------------------------

async def sync_credentials_to_db(db: AsyncSession) -> None:
    """Read credentials from disk and update DB if they changed.

    Call this after each SDK query() call.
    """
    disk_creds = _read_disk()
    if not disk_creds:
        return

    db_creds = await load_credentials_from_db(db)

    # Compare refresh tokens to detect change
    disk_rt = disk_creds.get("claudeAiOauth", {}).get("refreshToken")
    db_rt = (db_creds or {}).get("claudeAiOauth", {}).get("refreshToken")

    if disk_rt and disk_rt != db_rt:
        logger.warning("Credentials changed on disk, syncing to DB")
        await save_credentials_to_db(db, disk_creds)


# ---------------------------------------------------------------------------
# Manual refresh (kept for scheduler/pre-emptive refresh)
# ---------------------------------------------------------------------------

async def refresh_if_needed(db: AsyncSession | None = None) -> bool:
    """Check credentials expiry and refresh if less than 60 min remaining."""
    if not os.path.exists(CREDENTIALS_PATH):
        logger.warning("No credentials file found")
        return False

    try:
        with open(CREDENTIALS_PATH) as f:
            creds = json.load(f)

        oauth = creds.get("claudeAiOauth", {})
        expires_at = oauth.get("expiresAt", 0)
        refresh_token = oauth.get("refreshToken")

        if not refresh_token:
            logger.warning("No refresh token in credentials")
            return False

        now_ms = int(time.time() * 1000)
        remaining_min = (expires_at - now_ms) / 1000 / 60

        if remaining_min > 60:
            return True

        logger.info(f"Credentials expiring in {remaining_min:.0f} min, refreshing...")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                REFRESH_ENDPOINT,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": CLIENT_ID,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )

        if resp.status_code != 200:
            logger.warning(f"Refresh failed: {resp.status_code} {resp.text[:200]}")
            return False

        data = resp.json()
        new_access = data.get("access_token")
        new_refresh = data.get("refresh_token")
        expires_in = data.get("expires_in", 28800)

        if not new_access:
            logger.warning(f"No access token in refresh response: {data}")
            return False

        oauth["accessToken"] = new_access
        if new_refresh:
            oauth["refreshToken"] = new_refresh
        oauth["expiresAt"] = int(time.time() * 1000) + (expires_in * 1000)

        creds["claudeAiOauth"] = oauth
        _write_disk(creds)

        # Also persist to DB
        if db:
            await save_credentials_to_db(db, creds)

        logger.info(f"Credentials refreshed, valid for {expires_in // 60} minutes")
        return True

    except Exception as e:
        logger.warning(f"Credential refresh failed: {e}")
        return False

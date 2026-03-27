"""Auto-refresh Claude OAuth credentials before expiry.

Calls the Anthropic OAuth refresh endpoint directly and updates
the credentials file on disk.
"""
import json
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

CREDENTIALS_PATH = os.path.expanduser("~/.claude/.credentials.json")
REFRESH_ENDPOINT = "https://api.anthropic.com/v1/oauth/token"
CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"


async def refresh_if_needed() -> bool:
    """Check credentials expiry and refresh if less than 60 min remaining.

    Returns True if credentials are valid, False if refresh failed.
    """
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

        # Update credentials
        oauth["accessToken"] = new_access
        if new_refresh:
            oauth["refreshToken"] = new_refresh
        oauth["expiresAt"] = int(time.time() * 1000) + (expires_in * 1000)

        creds["claudeAiOauth"] = oauth

        with open(CREDENTIALS_PATH, "w") as f:
            json.dump(creds, f)
        os.chmod(CREDENTIALS_PATH, 0o600)

        logger.info(f"Credentials refreshed, valid for {expires_in // 60} minutes")
        return True

    except Exception as e:
        logger.warning(f"Credential refresh failed: {e}")
        return False

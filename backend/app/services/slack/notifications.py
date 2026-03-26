import uuid
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slack import SlackWorkspace, SlackChannelMapping, SlackUserMapping

logger = logging.getLogger(__name__)


async def get_bot_token(db: AsyncSession, org_id: uuid.UUID) -> str | None:
    result = await db.execute(select(SlackWorkspace).where(SlackWorkspace.org_id == org_id))
    workspace = result.scalar_one_or_none()
    return workspace.slack_bot_token if workspace else None


async def get_channel_id(
    db: AsyncSession,
    channel_type: str,
    org_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
) -> str | None:
    if channel_type == "project" and project_id:
        result = await db.execute(
            select(SlackChannelMapping).where(SlackChannelMapping.project_id == project_id)
        )
        mapping = result.scalar_one_or_none()
        return mapping.slack_channel_id if mapping else None
    elif channel_type == "org":
        result = await db.execute(select(SlackWorkspace).where(SlackWorkspace.org_id == org_id))
        workspace = result.scalar_one_or_none()
        return workspace.slack_org_channel_id if workspace else None
    return None


async def get_slack_user_id(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    result = await db.execute(select(SlackUserMapping).where(SlackUserMapping.user_id == user_id))
    mapping = result.scalar_one_or_none()
    return mapping.slack_user_id if mapping else None


async def send_slack_notification(
    db: AsyncSession,
    org_id: uuid.UUID,
    channel_type: str,  # "project" | "org" | "dm"
    project_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    blocks: list[dict] | None = None,
    text: str = "",
) -> bool:
    """Send a Slack notification. Returns True if sent, False if skipped."""
    try:
        from slack_sdk.web.async_client import AsyncWebClient  # noqa: PLC0415

        bot_token = await get_bot_token(db, org_id)
        if not bot_token:
            return False

        client = AsyncWebClient(token=bot_token)

        if channel_type == "dm" and user_id:
            slack_user_id = await get_slack_user_id(db, user_id)
            if not slack_user_id:
                return False
            # Open DM channel
            dm = await client.conversations_open(users=[slack_user_id])
            channel = dm["channel"]["id"]
        else:
            channel = await get_channel_id(db, channel_type, org_id, project_id)
            if not channel:
                return False

        resp = await client.chat_postMessage(channel=channel, text=text, blocks=blocks)
        if not resp.get("ok"):
            logger.warning(f"Slack API error: {resp.get('error')} (channel={channel})")
            return False
        return True

    except ImportError:
        logger.warning("slack_sdk is not installed; skipping Slack notification")
        return False
    except Exception as e:
        logger.warning(f"Slack notification failed: {e}", exc_info=True)
        return False

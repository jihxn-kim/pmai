"""Slack bot mention handler."""

import logging
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slack import SlackChannelMapping, SlackUserMapping, SlackWorkspace
from app.services.slack.formatters import (
    format_briefing_notification,
    format_error_message,
    format_my_tasks,
    format_project_status,
)
from app.services.slack.tools import execute_tool, parse_intent

logger = logging.getLogger(__name__)

try:
    from slack_sdk.web.async_client import AsyncWebClient  # noqa: F401
    HAS_SLACK_SDK = True
except ImportError:
    HAS_SLACK_SDK = False


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

async def resolve_user_from_slack(
    db: AsyncSession,
    slack_user_id: str,
) -> uuid.UUID | None:
    """Return the internal user UUID for a Slack user ID, or None."""
    result = await db.execute(
        select(SlackUserMapping).where(
            SlackUserMapping.slack_user_id == slack_user_id
        )
    )
    mapping = result.scalar_one_or_none()
    return mapping.user_id if mapping else None


async def resolve_org_from_channel(
    db: AsyncSession,
    slack_channel_id: str,
) -> uuid.UUID | None:
    """Return the org UUID associated with a Slack channel.

    Checks project channel mappings first, then workspace org channel.
    """
    # Check project channel mapping
    proj_result = await db.execute(
        select(SlackChannelMapping).where(
            SlackChannelMapping.slack_channel_id == slack_channel_id
        )
    )
    proj_mapping = proj_result.scalar_one_or_none()
    if proj_mapping:
        # Get org via project
        from app.models.project import Project  # noqa: PLC0415

        project_result = await db.execute(
            select(Project).where(Project.id == proj_mapping.project_id)
        )
        project = project_result.scalar_one_or_none()
        if project:
            return project.org_id

    # Check workspace org channel
    ws_result = await db.execute(
        select(SlackWorkspace).where(
            SlackWorkspace.slack_org_channel_id == slack_channel_id
        )
    )
    workspace = ws_result.scalar_one_or_none()
    if workspace:
        return workspace.org_id

    return None


# ---------------------------------------------------------------------------
# Result formatter
# ---------------------------------------------------------------------------

def _format_result(tool_name: str | None, result: dict) -> list[dict]:
    """Convert an execute_tool result dict into Slack Block Kit blocks."""
    if "error" in result:
        return format_error_message(result["error"])

    if tool_name == "get_project_status":
        return format_project_status(
            name=result.get("project_name", ""),
            progress=result.get("progress", 0.0),
            done=result.get("done", 0),
            total=result.get("total", 0),
            in_progress=result.get("in_progress", 0),
            open_prs=result.get("open_prs", 0),
        )

    if tool_name == "get_my_tasks":
        return format_my_tasks(result.get("tasks", []))

    if tool_name == "get_latest_briefing":
        org_summary = result.get("org_summary", {})
        week_start = result.get("week_start", "")
        return format_briefing_notification(org_summary, week_start)

    if tool_name in ("request_code_review", "run_project_analysis"):
        message = result.get("message", "작업이 요청되었습니다.")
        return [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"✅ {message}"},
            }
        ]

    if tool_name == "get_project_issues":
        issues = result.get("issues", [])
        project_name = result.get("project_name", "")
        if not issues:
            return [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✨ *{project_name}* 프로젝트에 문제점이 없습니다!",
                    },
                }
            ]
        lines = []
        for issue in issues[:10]:
            issue_type = issue.get("type", "")
            title = issue.get("title", "")
            emoji = {
                "overdue_task": "🔴",
                "stale_pr": "🟠",
                "pending_review": "🟡",
                "unassigned_task": "⚪",
            }.get(issue_type, "⚠️")
            lines.append(f"{emoji} {title}")
        return [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"⚠️ {project_name} 이슈 목록"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(lines)},
            },
        ]

    # Fallback
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": str(result)},
        }
    ]


# ---------------------------------------------------------------------------
# Main mention handler
# ---------------------------------------------------------------------------

async def handle_mention(
    db: AsyncSession,
    slack_event: dict,
    bot_token: str,
) -> None:
    """Process an app_mention event and reply in the same channel."""
    channel = slack_event.get("channel", "")
    raw_text: str = slack_event.get("text", "")
    slack_user_id: str = slack_event.get("user", "")

    # Strip mention tokens like <@UXXXXXXXX>
    clean_text = re.sub(r"<@[A-Z0-9]+>", "", raw_text).strip()

    # Resolve identities
    user_id = await resolve_user_from_slack(db, slack_user_id)
    org_id = await resolve_org_from_channel(db, channel)

    if not org_id:
        logger.warning("handle_mention: could not resolve org for channel %s", channel)
        blocks = format_error_message("이 채널에 연결된 조직을 찾을 수 없습니다.")
        await _send_reply(bot_token, channel, blocks)
        return

    if not user_id:
        # Still allow anonymous queries — use a nil UUID so services degrade gracefully
        user_id = uuid.UUID(int=0)

    # Parse intent via Claude
    intent = await parse_intent(clean_text)

    if intent["tool"] is None:
        # Claude returned a text clarification
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": intent["text"] or "무엇을 도와드릴까요?"},
            }
        ]
        await _send_reply(bot_token, channel, blocks)
        return

    # Execute the tool
    result = await execute_tool(
        db,
        tool_name=intent["tool"],
        tool_input=intent["input"],
        user_id=user_id,
        org_id=org_id,
    )

    blocks = _format_result(intent["tool"], result)
    await _send_reply(bot_token, channel, blocks)


async def _send_reply(bot_token: str, channel: str, blocks: list[dict]) -> None:
    """Send a Block Kit message to a Slack channel."""
    if not HAS_SLACK_SDK:
        logger.warning("slack_sdk is not installed; cannot send reply")
        return

    try:
        from slack_sdk.web.async_client import AsyncWebClient  # noqa: PLC0415

        client = AsyncWebClient(token=bot_token)
        text_fallback = " ".join(
            b.get("text", {}).get("text", "") if isinstance(b.get("text"), dict) else ""
            for b in blocks
        ).strip() or "응답이 준비되었습니다."
        await client.chat_postMessage(
            channel=channel,
            text=text_fallback,
            blocks=blocks,
        )
    except Exception as exc:
        logger.warning("_send_reply failed: %s", exc)

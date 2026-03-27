"""Slack bot mention handler — uses Claude Agent SDK for natural conversation."""

import logging
import os
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.slack import SlackChannelMapping, SlackUserMapping, SlackWorkspace

logger = logging.getLogger(__name__)

try:
    from slack_sdk.web.async_client import AsyncWebClient
    HAS_SLACK_SDK = True
except ImportError:
    HAS_SLACK_SDK = False

try:
    from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
    HAS_SDK = True
except ImportError:
    HAS_SDK = False


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

async def resolve_user_from_slack(
    db: AsyncSession,
    slack_user_id: str,
) -> uuid.UUID | None:
    result = await db.execute(
        select(SlackUserMapping).where(SlackUserMapping.slack_user_id == slack_user_id)
    )
    mapping = result.scalar_one_or_none()
    return mapping.user_id if mapping else None


async def resolve_org_from_channel(
    db: AsyncSession,
    slack_channel_id: str,
) -> uuid.UUID | None:
    proj_result = await db.execute(
        select(SlackChannelMapping).where(SlackChannelMapping.slack_channel_id == slack_channel_id)
    )
    proj_mapping = proj_result.scalar_one_or_none()
    if proj_mapping:
        from app.models.project import Project
        project_result = await db.execute(select(Project).where(Project.id == proj_mapping.project_id))
        project = project_result.scalar_one_or_none()
        if project:
            return project.org_id

    ws_result = await db.execute(
        select(SlackWorkspace).where(SlackWorkspace.slack_org_channel_id == slack_channel_id)
    )
    workspace = ws_result.scalar_one_or_none()
    if workspace:
        return workspace.org_id

    # Fallback: find workspace by any channel in the team
    ws_all = await db.execute(select(SlackWorkspace))
    for ws in ws_all.scalars():
        return ws.org_id

    return None


async def resolve_project_id_from_org(db: AsyncSession, org_id: uuid.UUID) -> str | None:
    from app.models.project import Project
    result = await db.execute(
        select(Project).where(Project.org_id == org_id).limit(1)
    )
    project = result.scalar_one_or_none()
    return str(project.id) if project else None


# ---------------------------------------------------------------------------
# Main mention handler
# ---------------------------------------------------------------------------

async def handle_mention(
    db: AsyncSession,
    slack_event: dict,
    bot_token: str,
) -> None:
    """Process an app_mention event — Claude converses naturally with PM tools."""
    channel = slack_event.get("channel", "")
    raw_text: str = slack_event.get("text", "")
    slack_user_id: str = slack_event.get("user", "")

    clean_text = re.sub(r"<@[A-Z0-9]+>", "", raw_text).strip()

    org_id = await resolve_org_from_channel(db, channel)
    if not org_id:
        await _send_reply(bot_token, channel, "이 채널에 연결된 조직을 찾을 수 없습니다.")
        return

    if not HAS_SDK:
        await _send_reply(bot_token, channel, "AI 서비스를 사용할 수 없습니다.")
        return

    # Get project_id for PM tools
    project_id = await resolve_project_id_from_org(db, org_id)

    # Build MCP servers for Claude
    mcp_servers = {}

    # PM Agent DB tools
    mcp_servers["pm_agent"] = {
        "command": "python",
        "args": ["-m", "app.services.ai.pm_mcp_server", str(org_id), project_id or ""],
        "env": {"DATABASE_URL": os.environ.get("DATABASE_URL", "")},
    }

    system_prompt = """당신은 PM Agent 슬랙 봇입니다. 프로젝트 관리를 도와주는 어시스턴트입니다.

사용자의 질문에 자연스럽게 대화하세요. PM Agent 도구를 사용해서 실제 데이터를 조회하고 답변하세요.

할 수 있는 일:
- 프로젝트 상태/진행률 조회
- 태스크 목록, 진행 상황 확인
- 팀 멤버 정보 조회
- 이슈/문제점 파악
- PR 현황 확인
- 최근 활동 내역

답변은 간결하게 Slack에 맞는 형식으로 하세요. 마크다운을 Slack 형식(*bold*, _italic_, `code`)으로 사용하세요.
반드시 한국어로 답변하세요."""

    allowed_tools = []
    if mcp_servers:
        allowed_tools.append("mcp__pm_agent__*")

    try:
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            max_turns=5,
            permission_mode="bypassPermissions",
        )
        if mcp_servers:
            options = ClaudeAgentOptions(
                system_prompt=system_prompt,
                allowed_tools=allowed_tools,
                mcp_servers=mcp_servers,
                max_turns=5,
                permission_mode="bypassPermissions",
            )

        result_text = None
        async for message in query(prompt=clean_text, options=options):
            if isinstance(message, ResultMessage):
                result_text = message.result

        if result_text:
            # Truncate for Slack 4000 char limit
            if len(result_text) > 3900:
                result_text = result_text[:3900] + "\n\n_...결과가 잘렸습니다._"
            await _send_reply(bot_token, channel, result_text)
        else:
            await _send_reply(bot_token, channel, "요청을 처리하지 못했습니다.")

    except Exception as e:
        logger.warning(f"handle_mention failed: {e}")
        await _send_reply(bot_token, channel, f"오류가 발생했습니다: {str(e)[:200]}")


async def _send_reply(bot_token: str, channel: str, text: str) -> None:
    """Send a text message to a Slack channel."""
    if not HAS_SLACK_SDK:
        logger.warning("slack_sdk is not installed; cannot send reply")
        return

    try:
        client = AsyncWebClient(token=bot_token)
        await client.chat_postMessage(channel=channel, text=text)
    except Exception as exc:
        logger.warning("_send_reply failed: %s", exc)

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

    # Build MCP servers for Claude
    mcp_servers = {}

    # PM Agent DB tools (no default project — Claude picks via get_org_projects)
    mcp_servers["pm_agent"] = {
        "command": "python",
        "args": ["-m", "app.services.ai.pm_mcp_server", str(org_id)],
        "env": {"DATABASE_URL": os.environ.get("DATABASE_URL", "")},
    }

    # GitHub MCP
    github_token = None
    try:
        from app.models.organization import Organization
        from app.services.github_service import get_installation_token
        org = await db.get(Organization, org_id)
        if org and org.github_installation_id:
            github_token = await get_installation_token(org.github_installation_id)
    except Exception:
        pass

    if github_token:
        mcp_servers["github"] = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_TOKEN": github_token},
        }

    allowed_tools = ["mcp__pm_agent__*"]
    if github_token:
        allowed_tools.append("mcp__github__*")

    system_prompt = """당신은 PM Agent 슬랙 봇입니다. 프로젝트 관리를 도와주는 풀스택 어시스턴트입니다.

사용자의 질문에 자연스럽게 대화하세요. 도구를 사용해서 실제 데이터를 조회하고 답변하세요.

## 사용 가능한 도구

### PM Agent 도구 (프로젝트 관리 데이터)
- 프로젝트 목록, 상태, 진행률 조회
- 태스크 목록, 멤버 정보, 이슈/문제점
- PR 현황, 최근 활동, AI 리뷰 결과

### GitHub MCP 도구 (코드 및 GitHub 데이터)
- 코드 파일 읽기, 커밋 히스토리 조회
- PR 생성/조회, 이슈 생성/조회
- 레포지토리 구조 탐색

## 할 수 있는 일
- 프로젝트 상태 확인, 태스크 관리
- GitHub 이슈 생성, PR 조회
- 코드 파일 내용 확인
- 프로젝트 분석 및 문제점 파악
- 팀 멤버 정보 조회

## 중요 규칙
- 사용자가 "프로젝트 뭐 있어?", "프로젝트 목록" 등을 물으면 반드시 get_org_projects를 먼저 호출하세요.
- 특정 프로젝트를 지정하지 않은 일반적인 질문에는 get_org_projects로 전체 목록을 먼저 보여주세요.

답변은 간결하게 Slack에 맞는 형식으로 하세요. 마크다운을 Slack 형식(*bold*, _italic_, `code`)으로 사용하세요.
반드시 한국어로 답변하세요."""

    try:
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            max_turns=10,
            permission_mode="bypassPermissions",
        )
        if mcp_servers:
            options = ClaudeAgentOptions(
                system_prompt=system_prompt,
                allowed_tools=allowed_tools,
                mcp_servers=mcp_servers,
                max_turns=10,
                permission_mode="bypassPermissions",
                debug_stderr=True,
            )

        result_text = None
        last_text = None
        async for message in query(prompt=clean_text, options=options):
            if isinstance(message, ResultMessage):
                result_text = message.result
            elif hasattr(message, "content"):
                content = message.content
                if isinstance(content, list):
                    for block in content:
                        if hasattr(block, "text") and block.text:
                            last_text = block.text
                elif isinstance(content, str) and content:
                    last_text = content

        final = result_text or last_text
        if final:
            if len(final) > 3900:
                final = final[:3900] + "\n\n_...결과가 잘렸습니다._"
            await _send_reply(bot_token, channel, final)
        else:
            await _send_reply(bot_token, channel, "요청을 처리하지 못했습니다.")

    except Exception as e:
        import traceback
        print(f"[SLACK BOT ERROR] {type(e).__name__}: {e}")
        print(traceback.format_exc()[-500:])
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

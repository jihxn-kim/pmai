"""Agent Executor: wraps Claude Agent SDK calls with SSE streaming.

Uses GitHub MCP server instead of git clone for repo access.
Returns plain text (markdown) results, no JSON parsing.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator, Callable

from app.config import settings
from app.services.ai.prompts import (
    CODE_REVIEWER_PROMPT,
    PROJECT_ANALYST_PROMPT,
    TEST_GENERATOR_PROMPT,
    WEEKLY_BRIEFING_PROMPT,
)

try:
    from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, AssistantMessage
    from claude_agent_sdk.types import StreamEvent
    HAS_SDK = True
except ImportError:
    query = None
    ClaudeAgentOptions = None
    ResultMessage = None
    AssistantMessage = None
    StreamEvent = None
    HAS_SDK = False

from app.services.ai.custom_tools import build_pm_tools_server

logger = logging.getLogger(__name__)


def _build_mcp_servers(github_token: str | None = None) -> dict:
    """Build MCP server config for GitHub access."""
    servers = {}
    if github_token:
        servers["github"] = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_TOKEN": github_token},
        }
    return servers


def _extract_stream_text(event: dict) -> str | None:
    """Extract text from a StreamEvent for progress display."""
    event_type = event.get("type")

    if event_type == "content_block_start":
        content_block = event.get("content_block", {})
        if content_block.get("type") == "tool_use":
            return f"🔧 Using {content_block.get('name', 'tool')}..."
        return None

    if event_type == "content_block_delta":
        delta = event.get("delta", {})
        if delta.get("type") == "text_delta":
            text = delta.get("text", "")
            if text.strip():
                return f"💬 {text[:200]}"
        if delta.get("type") == "thinking_delta":
            thinking = delta.get("thinking", "")
            if thinking.strip():
                return f"🧠 {thinking[:200]}"
        return None

    if event_type == "content_block_stop":
        return None

    return None


def _extract_message_text(message) -> str | None:
    """Extract human-readable text from a complete AssistantMessage."""
    if not hasattr(message, "content"):
        return None

    content = message.content
    if isinstance(content, str):
        return f"💬 {content[:300]}"
    if isinstance(content, list):
        parts = []
        for block in content:
            block_type = getattr(block, "type", "")
            if block_type == "thinking" or hasattr(block, "thinking"):
                thinking = getattr(block, "thinking", "")
                if thinking:
                    parts.append(f"🧠 {thinking[:300]}")
            elif hasattr(block, "name"):
                tool_input = getattr(block, "input", {})
                if isinstance(tool_input, dict):
                    path = tool_input.get("file_path") or tool_input.get("path") or tool_input.get("command", "")
                    parts.append(f"🔧 {block.name} → {str(path)[:150]}")
                else:
                    parts.append(f"🔧 {block.name}")
            elif hasattr(block, "text") and block.text:
                parts.append(f"💬 {block.text[:300]}")
        return "\n".join(parts) if parts else None
    return None


async def run_agent_stream(
    system_prompt: str,
    user_prompt: str,
    cwd: str | None = None,
    github_token: str | None = None,
    extra_tools: list[str] | None = None,
    project_id: str | None = None,
    org_id: str | None = None,
) -> AsyncGenerator[dict, None]:
    """Async generator that yields progress events then the final result.

    Yields:
      {"type": "progress", "message": "..."}
      {"type": "result", "data": "...text..."}
      {"type": "error", "message": "..."}
    """
    if not HAS_SDK:
        yield {"type": "error", "message": "claude-agent-sdk is not installed"}
        return

    # Build tools list
    allowed_tools = ["Read", "Glob", "Grep", "Bash"]
    if extra_tools:
        allowed_tools.extend(extra_tools)

    # Add GitHub MCP if token provided
    mcp_servers = _build_mcp_servers(github_token)
    if mcp_servers:
        allowed_tools.append("mcp__github__*")

    # Add PM Agent DB tools as separate process MCP server
    if project_id or org_id:
        import os
        mcp_servers["pm_agent"] = {
            "command": "python",
            "args": ["-m", "app.services.ai.pm_mcp_server", org_id or "", project_id or ""],
            "env": {"DATABASE_URL": os.environ.get("DATABASE_URL", "")},
        }
        allowed_tools.append("mcp__pm_agent__*")

    options_kwargs = {
        "allowed_tools": allowed_tools,
        "system_prompt": system_prompt,
        "model": settings.ai_model,
        "max_turns": settings.ai_max_turns,
        "permission_mode": "bypassPermissions",
        "include_partial_messages": True,
        "debug_stderr": True,
    }
    if cwd:
        options_kwargs["cwd"] = cwd
    if mcp_servers:
        options_kwargs["mcp_servers"] = mcp_servers

    options = ClaudeAgentOptions(**options_kwargs)

    raw_output = None
    last_text = None
    try:
        async for message in query(prompt=user_prompt, options=options):
            # Handle StreamEvent (partial messages)
            if StreamEvent is not None and isinstance(message, StreamEvent):
                text = _extract_stream_text(message.event)
                if text:
                    yield {"type": "progress", "message": text}
                continue

            # Handle ResultMessage
            if ResultMessage is not None and isinstance(message, ResultMessage):
                raw_output = (
                    getattr(message, "result", None)
                    or getattr(message, "content", None)
                    or getattr(message, "text", None)
                )
                break

            # Capture assistant text as fallback (no progress yield — delta already sent above)
            if hasattr(message, "content"):
                content = message.content
                if isinstance(content, list):
                    for block in content:
                        if hasattr(block, "text") and block.text:
                            last_text = block.text
                elif isinstance(content, str) and content:
                    last_text = content

    except Exception as exc:
        import traceback
        error_detail = f"{type(exc).__name__}: {exc}"
        # Try to get stderr from ProcessError
        stderr_output = getattr(exc, 'stderr', None) or getattr(exc, 'error_output', None) or ""
        if stderr_output:
            error_detail += f"\nSTDERR: {stderr_output[:500]}"
        error_detail += f"\n{traceback.format_exc()[-300:]}"
        logger.error("Agent SDK error: %s", error_detail)
        yield {"type": "error", "message": error_detail[:1000]}
        return

    if raw_output is None and last_text:
        raw_output = last_text

    if raw_output is None:
        yield {"type": "error", "message": "Agent produced no output"}
        return

    yield {"type": "result", "data": raw_output}


# ---------------------------------------------------------------------------
# Non-streaming wrapper
# ---------------------------------------------------------------------------

async def run_agent(system_prompt: str, user_prompt: str, cwd: str | None = None, github_token: str | None = None, project_id: str | None = None) -> str:
    """Run agent and return the final result as plain text."""
    async for event in run_agent_stream(system_prompt, user_prompt, cwd=cwd, github_token=github_token, project_id=project_id):
        if event["type"] == "result":
            return event["data"]
        if event["type"] == "error":
            raise RuntimeError(event["message"])
    raise ValueError("Agent stream ended without result")


# ---------------------------------------------------------------------------
# High-level task runners (use GitHub MCP, no clone needed)
# ---------------------------------------------------------------------------

async def run_code_review(github_token: str, repo_owner: str, repo_name: str, pr_number: int, base: str, head: str) -> str:
    user_prompt = (
        f"Review PR #{pr_number} in {repo_owner}/{repo_name}.\n"
        f"Base branch: {base}, Head branch: {head}\n\n"
        f"Use the GitHub MCP tools to fetch the PR diff and examine the changes. "
        f"Provide a thorough code review."
    )
    return await run_agent(CODE_REVIEWER_PROMPT, user_prompt, github_token=github_token)


async def run_project_analysis(github_token: str, repo_owner: str, repo_name: str, project_id: str | None = None) -> str:
    user_prompt = (
        f"{repo_owner}/{repo_name} 프로젝트의 현재 상태를 분석하세요.\n\n"
        f"다음 도구들을 활용하세요:\n"
        f"- GitHub MCP 도구: 커밋, PR, 이슈, 파일 구조 조회\n"
        f"- PM Agent 도구: get_project_tasks, get_project_progress, get_project_issues, get_project_members, get_pull_requests\n\n"
        f"코드와 프로젝트 관리 데이터를 모두 결합해서 종합 분석을 제공하세요."
    )
    return await run_agent(PROJECT_ANALYST_PROMPT, user_prompt, github_token=github_token, project_id=project_id)


async def run_test_generation(github_token: str, repo_owner: str, repo_name: str, pr_number: int | None, file_paths: list[str] | None, base: str | None, head: str | None) -> str:
    if pr_number:
        user_prompt = (
            f"Generate test scenarios for PR #{pr_number} in {repo_owner}/{repo_name}.\n"
            f"Use the GitHub MCP tools to fetch the PR changes and generate comprehensive test scenarios."
        )
    else:
        files_str = "\n".join(f"- {p}" for p in (file_paths or []))
        user_prompt = (
            f"Generate test scenarios for these files in {repo_owner}/{repo_name}:\n{files_str}\n\n"
            f"Use the GitHub MCP tools to read the files and generate test scenarios."
        )
    return await run_agent(TEST_GENERATOR_PROMPT, user_prompt, github_token=github_token)


async def run_weekly_briefing(github_token: str, repo_owner: str, repo_name: str, context: str) -> str:
    user_prompt = (
        f"Generate a weekly briefing for the {repo_owner}/{repo_name} project.\n\n"
        f"Project data:\n{context}\n\n"
        f"Use the GitHub MCP tools to examine recent activity and provide the briefing."
    )
    return await run_agent(WEEKLY_BRIEFING_PROMPT, user_prompt, github_token=github_token)


# Streaming versions for SSE endpoints
async def stream_project_analysis(github_token: str, repo_owner: str, repo_name: str, project_id: str | None = None, org_id: str | None = None) -> AsyncGenerator[dict, None]:
    user_prompt = (
        f"{repo_owner}/{repo_name} 프로젝트의 현재 상태를 분석하세요.\n\n"
        f"다음 도구들을 활용하세요:\n"
        f"- GitHub MCP 도구: 커밋, PR, 이슈, 파일 구조 조회\n"
        f"- PM Agent 도구: get_project_tasks, get_project_progress, get_project_issues, get_project_members, get_pull_requests\n\n"
        f"코드와 프로젝트 관리 데이터를 모두 결합해서 종합 분석을 제공하세요."
    )
    async for event in run_agent_stream(PROJECT_ANALYST_PROMPT, user_prompt, github_token=github_token, project_id=project_id, org_id=org_id):
        yield event

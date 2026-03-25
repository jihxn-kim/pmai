"""Agent Executor: manages repo cloning and wraps Claude Agent SDK calls.

Uses SSE streaming — the run_agent_stream() async generator yields progress
messages as they arrive, then yields the final parsed JSON result.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
from typing import AsyncGenerator

from app.config import settings
from app.services.github_service import get_installation_token
from app.services.ai.prompts import (
    CODE_REVIEWER_PROMPT,
    PROJECT_ANALYST_PROMPT,
    TEST_GENERATOR_PROMPT,
    WEEKLY_BRIEFING_PROMPT,
)

try:
    from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, AssistantMessage
except ImportError:
    query = None
    ClaudeAgentOptions = None
    ResultMessage = None
    AssistantMessage = None

logger = logging.getLogger(__name__)


async def clone_or_update_repo(
    project_id: str,
    job_id: str,
    repo_url: str,
    installation_id: int,
) -> str:
    """Clone the repo to an isolated directory for this job and return the path."""
    token = await get_installation_token(installation_id)
    authenticated_url = repo_url.replace("https://", f"https://x-access-token:{token}@")

    repo_path = os.path.join(settings.ai_repo_base_path, str(project_id), str(job_id))
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)
    os.makedirs(repo_path, exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--depth", "50", authenticated_url, repo_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        err_msg = stderr.decode(errors="replace").strip().replace(token, "<token>")
        raise RuntimeError(f"git clone failed: {err_msg}")

    return repo_path


def cleanup_repo(project_id: str, job_id: str) -> None:
    """Remove the job-specific repo directory."""
    repo_path = os.path.join(settings.ai_repo_base_path, str(project_id), str(job_id))
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path, ignore_errors=True)


def _extract_message_text(message) -> str | None:
    """Extract human-readable text from an Agent SDK message."""
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
                # Tool use block
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
    repo_path: str,
    system_prompt: str,
    user_prompt: str,
) -> AsyncGenerator[dict, None]:
    """Async generator that yields progress events then the final result.

    Yields dicts with:
      {"type": "progress", "message": "..."}
      {"type": "result", "data": {...parsed JSON...}}
      {"type": "error", "message": "..."}
    """
    if query is None:
        yield {"type": "error", "message": "claude-agent-sdk is not installed"}
        return

    options = ClaudeAgentOptions(
        cwd=repo_path,
        allowed_tools=["Read", "Glob", "Grep", "Bash"],
        system_prompt=system_prompt,
        model=settings.ai_model,
        max_turns=settings.ai_max_turns,
        permission_mode="bypassPermissions",
    )

    raw_output = None
    last_text = None  # Track last assistant text as fallback
    try:
        # Use an async iterator with heartbeat to prevent connection timeout
        aiter = query(prompt=user_prompt, options=options).__aiter__()
        while True:
            try:
                message = await asyncio.wait_for(aiter.__anext__(), timeout=15.0)
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                # No message in 15s — send heartbeat to keep connection alive
                yield {"type": "heartbeat"}
                continue

            msg_type = type(message).__name__
            logger.info("Agent message: type=%s, attrs=%s", msg_type, [a for a in dir(message) if not a.startswith("_")])

            if ResultMessage is not None and isinstance(message, ResultMessage):
                # Try multiple possible attribute names
                raw_output = (
                    getattr(message, "result", None)
                    or getattr(message, "content", None)
                    or getattr(message, "text", None)
                )
                # If result is still None, check if it's a stop message with content elsewhere
                if raw_output is None and hasattr(message, "stop_reason"):
                    logger.warning("ResultMessage has stop_reason=%s but no result text", message.stop_reason)
                yield {"type": "progress", "message": f"✅ 분석 완료 ({msg_type})"}
                break

            # Capture assistant text blocks as fallback result
            if hasattr(message, "content"):
                content = message.content
                if isinstance(content, list):
                    for block in content:
                        if hasattr(block, "text") and block.text:
                            last_text = block.text
                elif isinstance(content, str) and content:
                    last_text = content

            # Yield progress only for meaningful messages (skip SystemMessage, UserMessage, RateLimitEvent)
            text = _extract_message_text(message)
            if text:
                yield {"type": "progress", "message": text}

    except Exception as exc:
        yield {"type": "error", "message": str(exc)[:500]}
        return

    # Use last_text as fallback if no explicit ResultMessage
    if raw_output is None and last_text:
        raw_output = last_text
        logger.info("Using last assistant text as fallback result (%d chars)", len(last_text))

    if raw_output is None:
        yield {"type": "error", "message": "Agent produced no output"}
        return

    # Parse JSON from result
    stripped = raw_output.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if match:
        stripped = match.group(1).strip()

    try:
        parsed = json.loads(stripped)
        yield {"type": "result", "data": parsed}
    except json.JSONDecodeError:
        # Return raw text as result if not JSON
        yield {"type": "result", "data": {"summary": raw_output[:2000]}}


# ---------------------------------------------------------------------------
# Non-streaming wrapper (for backward compat with worker/webhooks)
# ---------------------------------------------------------------------------

async def run_agent(repo_path: str, system_prompt: str, user_prompt: str) -> dict:
    """Run agent and return only the final result dict."""
    async for event in run_agent_stream(repo_path, system_prompt, user_prompt):
        if event["type"] == "result":
            return event["data"]
        if event["type"] == "error":
            raise RuntimeError(event["message"])
    raise ValueError("Agent stream ended without result")


# ---------------------------------------------------------------------------
# High-level task runners
# ---------------------------------------------------------------------------

async def run_code_review(repo_path: str, pr_number: int, base: str, head: str) -> dict:
    user_prompt = (
        f"Review PR #{pr_number}.\n"
        f"Base branch: {base}, Head branch: {head}\n\n"
        f"Run `git diff origin/{base}...origin/{head}` to see changes, then examine "
        f"affected files. Return the review as a JSON object."
    )
    return await run_agent(repo_path, CODE_REVIEWER_PROMPT, user_prompt)


async def run_project_analysis(repo_path: str, context: dict) -> dict:
    user_prompt = (
        "Analyse the current state of this project.\n\n"
        f"Project context:\n{json.dumps(context, indent=2, default=str)}\n\n"
        "Examine git history and repo structure, then return the analysis as JSON."
    )
    return await run_agent(repo_path, PROJECT_ANALYST_PROMPT, user_prompt)


async def run_test_generation(repo_path: str, pr_number: int, file_paths: list[str], base: str, head: str) -> dict:
    files_list = "\n".join(f"- {p}" for p in (file_paths or []))
    user_prompt = (
        f"Generate test scenarios for PR #{pr_number}.\n"
        f"Base: {base}, Head: {head}\n"
        f"Changed files:\n{files_list}\n\n"
        f"Return test scenarios as JSON."
    )
    return await run_agent(repo_path, TEST_GENERATOR_PROMPT, user_prompt)


async def run_weekly_briefing(repo_path: str, context: dict) -> dict:
    user_prompt = (
        "Generate a weekly briefing for this project.\n\n"
        f"Project data:\n{json.dumps(context, indent=2, default=str)}\n\n"
        "Examine recent git history and return the briefing as JSON."
    )
    return await run_agent(repo_path, WEEKLY_BRIEFING_PROMPT, user_prompt)


# Streaming versions for SSE endpoints
async def stream_project_analysis(repo_path: str, context: dict) -> AsyncGenerator[dict, None]:
    user_prompt = (
        "Analyse the current state of this project.\n\n"
        f"Project context:\n{json.dumps(context, indent=2, default=str)}\n\n"
        "Examine git history and repo structure, then return the analysis as JSON."
    )
    async for event in run_agent_stream(repo_path, PROJECT_ANALYST_PROMPT, user_prompt):
        yield event


async def stream_code_review(repo_path: str, pr_number: int, base: str, head: str) -> AsyncGenerator[dict, None]:
    user_prompt = (
        f"Review PR #{pr_number}.\n"
        f"Base branch: {base}, Head branch: {head}\n\n"
        f"Run `git diff origin/{base}...origin/{head}` to see changes, then examine "
        f"affected files. Return the review as a JSON object."
    )
    async for event in run_agent_stream(repo_path, CODE_REVIEWER_PROMPT, user_prompt):
        yield event

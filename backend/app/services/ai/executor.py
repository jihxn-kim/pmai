"""Agent Executor: manages repo cloning and wraps Claude Agent SDK calls."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
from typing import Callable

from app.config import settings
from app.services.github_service import get_installation_token
from app.services.ai.prompts import (
    CODE_REVIEWER_PROMPT,
    PROJECT_ANALYST_PROMPT,
    TEST_GENERATOR_PROMPT,
    WEEKLY_BRIEFING_PROMPT,
)

try:
    from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
except ImportError:
    query = None
    ClaudeAgentOptions = None
    ResultMessage = None

logger = logging.getLogger(__name__)


async def clone_or_update_repo(
    project_id: str,
    job_id: str,
    repo_url: str,
    installation_id: int,
) -> str:
    """Clone the repo to an isolated directory for this job and return the path.

    Uses a shallow clone (--depth 50) with an embedded installation token so
    the subprocess never needs separate credential storage.
    """
    token = await get_installation_token(installation_id)

    # Embed token into the HTTPS URL: https://x-access-token:<token>@github.com/...
    authenticated_url = repo_url.replace("https://", f"https://x-access-token:{token}@")

    repo_path = os.path.join(settings.ai_repo_base_path, str(project_id), str(job_id))
    os.makedirs(repo_path, exist_ok=True)

    logger.info("Cloning repo %s to %s", repo_url, repo_path)

    proc = await asyncio.create_subprocess_exec(
        "git",
        "clone",
        "--depth",
        "50",
        authenticated_url,
        repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        err_msg = stderr.decode(errors="replace").strip()
        # Scrub the token from error messages before logging/raising
        err_msg = err_msg.replace(token, "<token>")
        raise RuntimeError(f"git clone failed (exit {proc.returncode}): {err_msg}")

    logger.info("Repo cloned successfully to %s", repo_path)
    return repo_path


def cleanup_repo(project_id: str, job_id: str) -> None:
    """Remove the job-specific repo directory."""
    repo_path = os.path.join(settings.ai_repo_base_path, str(project_id), str(job_id))
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)
        logger.info("Cleaned up repo directory %s", repo_path)
    else:
        logger.warning("cleanup_repo: path does not exist: %s", repo_path)


async def run_agent(
    repo_path: str,
    system_prompt: str,
    user_prompt: str,
    on_progress: Callable | None = None,
) -> dict:
    """Invoke the Claude Agent SDK and return the parsed JSON result.

    The Agent SDK uses anyio internally, which conflicts with FastAPI's asyncio
    event loop when called via asyncio.create_task(). To avoid this, we run the
    SDK in a separate thread with its own event loop using anyio.run().

    Args:
        on_progress: optional callback(message_str) called with each intermediate
                     agent message (tool use, thinking, etc.)
    """
    if query is None:
        raise RuntimeError(
            "claude_agent_sdk is not installed. "
            "Install it with: pip install claude-agent-sdk"
        )

    import asyncio
    import concurrent.futures

    progress_log: list[str] = []

    def _run_in_thread() -> str | None:
        """Run Agent SDK in a new thread with its own event loop via anyio."""
        import anyio

        async def _inner() -> str | None:
            options = ClaudeAgentOptions(
                cwd=repo_path,
                allowed_tools=["Read", "Glob", "Grep", "Bash"],
                system_prompt=system_prompt,
                model=settings.ai_model,
                max_turns=settings.ai_max_turns,
                permission_mode="bypassPermissions",
            )

            raw_output: str | None = None
            async for message in query(prompt=user_prompt, options=options):
                if ResultMessage is not None and isinstance(message, ResultMessage):
                    raw_output = message.result if hasattr(message, 'result') else getattr(message, 'content', None)
                    break
                else:
                    # Capture intermediate messages for progress
                    msg_type = type(message).__name__
                    msg_text = ""
                    if hasattr(message, 'content'):
                        content = message.content
                        if isinstance(content, list):
                            for block in content:
                                if hasattr(block, 'text'):
                                    msg_text = block.text[:200]
                                    break
                                elif hasattr(block, 'name'):
                                    # Tool use block
                                    tool_input = getattr(block, 'input', {})
                                    if isinstance(tool_input, dict):
                                        file_path = tool_input.get('file_path') or tool_input.get('path') or tool_input.get('command', '')
                                        msg_text = f"Tool: {block.name} → {str(file_path)[:100]}"
                                    else:
                                        msg_text = f"Tool: {block.name}"
                                    break
                        elif isinstance(content, str):
                            msg_text = content[:200]
                    if not msg_text:
                        msg_text = str(message)[:200]

                    progress_log.append(f"[{msg_type}] {msg_text}")
                    if on_progress and progress_log:
                        try:
                            on_progress(progress_log[-1])
                        except Exception:
                            pass
            return raw_output

        return anyio.run(_inner)

    # Run in a separate thread so we don't conflict with FastAPI's event loop
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        raw_output = await loop.run_in_executor(pool, _run_in_thread)

    if raw_output is None:
        raise ValueError("Agent produced no ResultMessage output")

    # Strip optional markdown code-block wrapper: ```json ... ```
    stripped = raw_output.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if match:
        stripped = match.group(1).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Agent output could not be parsed as JSON: {exc}\nRaw output:\n{raw_output}"
        ) from exc


# ---------------------------------------------------------------------------
# High-level task runners
# ---------------------------------------------------------------------------


async def run_code_review(
    repo_path: str,
    pr_number: int,
    base: str,
    head: str,
    on_progress: Callable | None = None,
) -> dict:
    """Run a code review agent for the given PR diff."""
    user_prompt = (
        f"Review PR #{pr_number}.\n"
        f"Base branch: {base}\n"
        f"Head branch: {head}\n\n"
        f"Run `git diff {base}...{head}` to see the changes, then examine the "
        f"affected files in detail. Produce a thorough review according to the "
        f"instructions in your system prompt and return the result as a JSON object."
    )
    return await run_agent(repo_path, CODE_REVIEWER_PROMPT, user_prompt, on_progress)


async def run_project_analysis(repo_path: str, context: dict, on_progress: callable | None = None) -> dict:
    """Run a project analysis agent using the supplied context payload."""
    user_prompt = (
        "Analyse the current state of this project.\n\n"
        f"Project context (tasks, PRs, team):\n{json.dumps(context, indent=2)}\n\n"
        "Examine recent git history (`git log --oneline -50`) and any other "
        "relevant repository information you need, then return the analysis as "
        "a JSON object."
    )
    return await run_agent(repo_path, PROJECT_ANALYST_PROMPT, user_prompt, on_progress)


async def run_test_generation(
    repo_path: str,
    pr_number: int,
    file_paths: list[str],
    base: str,
    head: str,
    on_progress: Callable | None = None,
) -> dict:
    """Generate test scenarios for the changed files in a PR."""
    files_list = "\n".join(f"- {p}" for p in file_paths)
    user_prompt = (
        f"Generate test scenarios for PR #{pr_number}.\n"
        f"Base branch: {base}\n"
        f"Head branch: {head}\n\n"
        f"Changed files:\n{files_list}\n\n"
        f"Run `git diff {base}...{head}` and read the changed files to understand "
        f"what each change does. Then produce comprehensive test scenarios according "
        f"to the instructions in your system prompt and return the result as a JSON object."
    )
    return await run_agent(repo_path, TEST_GENERATOR_PROMPT, user_prompt, on_progress)


async def run_weekly_briefing(repo_path: str, context: dict, on_progress: callable | None = None) -> dict:
    """Generate a weekly project briefing using the supplied context payload."""
    user_prompt = (
        "Generate a weekly briefing for this project.\n\n"
        f"Project data (tasks, PRs, members, activity):\n{json.dumps(context, indent=2)}\n\n"
        "Also examine recent git history (`git log --oneline --since='7 days ago'`) "
        "for additional context, then return the briefing as a JSON object."
    )
    return await run_agent(repo_path, WEEKLY_BRIEFING_PROMPT, user_prompt, on_progress)

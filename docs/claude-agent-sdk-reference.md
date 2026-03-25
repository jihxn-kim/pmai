# Claude Agent SDK Reference

PM Agent에서 사용하는 Claude Agent SDK의 핵심 내용을 정리한 문서입니다.
전체 공식 문서: https://platform.claude.com/docs/en/agent-sdk

---

## 목차

1. [설치 및 기본 사용](#설치-및-기본-사용)
2. [메시지 타입](#메시지-타입)
3. [스트리밍 출력](#스트리밍-출력)
4. [입력 모드](#입력-모드)
5. [권한 시스템](#권한-시스템)
6. [사용자 입력 처리](#사용자-입력-처리)
7. [Hooks](#hooks)
8. [서브에이전트](#서브에이전트)
9. [세션 관리](#세션-관리)
10. [MCP 연동](#mcp-연동)
11. [커스텀 도구](#커스텀-도구)
12. [구조화된 출력](#구조화된-출력)
13. [시스템 프롬프트](#시스템-프롬프트)
14. [Skills](#skills)
15. [슬래시 명령어](#슬래시-명령어)
16. [플러그인](#플러그인)
17. [마이그레이션 가이드](#마이그레이션-가이드)

---

## 설치 및 기본 사용

공식 문서: https://platform.claude.com/docs/en/agent-sdk/overview

```bash
pip install claude-agent-sdk
```

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    async for message in query(
        prompt="What files are in this directory?",
        options=ClaudeAgentOptions(allowed_tools=["Bash", "Glob"]),
    ):
        if hasattr(message, "result"):
            print(message.result)

asyncio.run(main())
```

### 내장 도구

| Tool | 설명 |
|------|------|
| Read | 파일 읽기 |
| Write | 파일 생성 |
| Edit | 파일 수정 |
| Bash | 터미널 명령 실행 |
| Glob | 패턴으로 파일 찾기 |
| Grep | 파일 내용 검색 |
| WebSearch | 웹 검색 |
| WebFetch | 웹 페이지 가져오기 |
| AskUserQuestion | 사용자에게 질문 |
| Agent | 서브에이전트 호출 |

### 인증

- `ANTHROPIC_API_KEY` 환경변수
- Amazon Bedrock: `CLAUDE_CODE_USE_BEDROCK=1`
- Google Vertex AI: `CLAUDE_CODE_USE_VERTEX=1`
- Microsoft Azure: `CLAUDE_CODE_USE_FOUNDRY=1`

---

## 메시지 타입

공식 문서: https://platform.claude.com/docs/en/agent-sdk/overview

```
┌──────────────────────┬──────────────────────────────────────────────┐
│ 메시지 타입           │ 내용                                         │
├──────────────────────┼──────────────────────────────────────────────┤
│ SystemMessage        │ 세션 시작 (session_id 포함)                   │
│ AssistantMessage     │ Claude의 응답 (thinking, text, tool_use 블록) │
│ UserMessage          │ 도구 실행 결과 반환                           │
│ ResultMessage        │ 최종 결과 (result 속성)                       │
│ StreamEvent          │ 실시간 토큰 스트리밍 (partial_messages 활성화 시)│
│ RateLimitEvent       │ API 속도 제한 상태 변경                       │
└──────────────────────┴──────────────────────────────────────────────┘
```

### AssistantMessage content 블록

```
┌────────────────────┬────────────────────────────────────────────────┐
│ 블록 타입           │ 내용                                           │
├────────────────────┼────────────────────────────────────────────────┤
│ thinking           │ Claude의 내부 사고 과정 (🧠)                    │
│ text               │ 사용자에게 보여주는 설명/응답 (💬)              │
│ tool_use           │ 도구 호출 — name, input 포함 (🔧)              │
└────────────────────┴────────────────────────────────────────────────┘
```

### 메시지 처리 예시

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

async for message in query(prompt="버그 고쳐줘", options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if block.type == "thinking":
                print("🧠", block.thinking)
            elif block.type == "text":
                print("💬", block.text)
            elif block.type == "tool_use":
                print("🔧", block.name, block.input)
    elif isinstance(message, ResultMessage):
        print("✅ 완료:", message.result)
```

---

## 스트리밍 출력

공식 문서: https://platform.claude.com/docs/en/agent-sdk/streaming-output

`include_partial_messages=True` 설정 시 토큰 단위 스트리밍:

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import StreamEvent

async for message in query(
    prompt="파일 목록 보여줘",
    options=ClaudeAgentOptions(
        include_partial_messages=True,
        allowed_tools=["Bash", "Read"],
    ),
):
    if isinstance(message, StreamEvent):
        event = message.event
        if event.get("type") == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                print(delta.get("text", ""), end="", flush=True)
            elif delta.get("type") == "input_json_delta":
                print(delta.get("partial_json", ""), end="")
```

### StreamEvent 구조

```python
@dataclass
class StreamEvent:
    uuid: str                          # 고유 식별자
    session_id: str                    # 세션 ID
    event: dict[str, Any]              # Claude API 원시 스트림 이벤트
    parent_tool_use_id: str | None     # 서브에이전트 내부인 경우 부모 ID
```

### 이벤트 타입

| Event Type | 설명 |
|:-----------|:-----|
| message_start | 새 메시지 시작 |
| content_block_start | 새 콘텐츠 블록 시작 (텍스트 또는 도구 사용) |
| content_block_delta | 증분 업데이트 |
| content_block_stop | 콘텐츠 블록 종료 |
| message_delta | 메시지 레벨 업데이트 (stop reason, usage) |
| message_stop | 메시지 종료 |

### 메시지 흐름

```
StreamEvent (message_start)
StreamEvent (content_block_start) - text block
StreamEvent (content_block_delta) - text chunks...
StreamEvent (content_block_stop)
StreamEvent (content_block_start) - tool_use block
StreamEvent (content_block_delta) - tool input chunks...
StreamEvent (content_block_stop)
StreamEvent (message_delta)
StreamEvent (message_stop)
AssistantMessage - 완전한 메시지
... tool 실행 ...
ResultMessage - 최종 결과
```

### 스트리밍 UI 예시

```python
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from claude_agent_sdk.types import StreamEvent

in_tool = False

async for message in query(
    prompt="TODO 코멘트 찾아줘",
    options=ClaudeAgentOptions(
        include_partial_messages=True,
        allowed_tools=["Read", "Bash", "Grep"],
    ),
):
    if isinstance(message, StreamEvent):
        event = message.event
        event_type = event.get("type")

        if event_type == "content_block_start":
            content_block = event.get("content_block", {})
            if content_block.get("type") == "tool_use":
                tool_name = content_block.get("name")
                print(f"\n[Using {tool_name}...]", end="", flush=True)
                in_tool = True

        elif event_type == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta" and not in_tool:
                print(delta.get("text", ""), end="", flush=True)

        elif event_type == "content_block_stop":
            if in_tool:
                print(" done", flush=True)
                in_tool = False

    elif isinstance(message, ResultMessage):
        print(f"\n\n--- Complete ---")
```

### 알려진 제한사항

- **Extended thinking**: `max_thinking_tokens` 설정 시 StreamEvent가 발생하지 않음
- **Structured output**: JSON 결과는 최종 ResultMessage.structured_output에서만 제공

---

## 입력 모드

공식 문서: https://platform.claude.com/docs/en/agent-sdk/streaming-vs-single-mode

### Streaming Input Mode (권장)

`ClaudeSDKClient`를 사용한 장기 실행 대화형 세션:

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock

async with ClaudeSDKClient(options=ClaudeAgentOptions(
    allowed_tools=["Read", "Grep"],
)) as client:
    await client.query("Auth 모듈 분석해줘")
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)

    # 같은 세션에서 후속 질문
    await client.query("이제 JWT로 리팩토링해줘")
    async for message in client.receive_response():
        ...
```

지원 기능: 이미지 첨부, 메시지 큐잉, 인터럽트, 도구 통합, Hooks, 실시간 피드백, 컨텍스트 유지

### Single Message Input

간단한 일회성 쿼리:

```python
async for message in query(
    prompt="인증 흐름 설명해줘",
    options=ClaudeAgentOptions(max_turns=1, allowed_tools=["Read", "Grep"]),
):
    if isinstance(message, ResultMessage):
        print(message.result)
```

제한사항: 이미지 첨부 불가, 인터럽트 불가, Hook 미지원

---

## 권한 시스템

공식 문서: https://platform.claude.com/docs/en/agent-sdk/permissions

### 권한 평가 순서

1. **Hooks** — allow, deny, 또는 다음 단계로 진행
2. **Deny rules** — `disallowed_tools`로 차단
3. **Permission mode** — 전역 모드 적용
4. **Allow rules** — `allowed_tools`로 승인
5. **canUseTool 콜백** — 위에서 결정 안 된 경우 호출

### Permission Modes

| Mode | 설명 | 동작 |
|:-----|:-----|:-----|
| default | 기본 | 미승인 도구는 canUseTool 콜백 호출 |
| acceptEdits | 파일 수정 자동 승인 | Edit, Write, 파일시스템 명령 자동 승인 |
| bypassPermissions | 모든 권한 우회 | 모든 도구 자동 승인 (주의!) |
| plan | 계획 모드 | 도구 실행 없음, 분석/계획만 |
| dontAsk (TS only) | 거부 모드 | 미승인 도구는 즉시 거부 |

### Allow/Deny 규칙

```python
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Grep"],           # 이것만 자동 승인
    disallowed_tools=["Bash"],                 # 이건 항상 차단 (bypassPermissions에서도)
    permission_mode="acceptEdits",             # 파일 수정도 자동 승인
)
```

주의: `allowed_tools`는 `bypassPermissions`를 제한하지 않음. 차단하려면 `disallowed_tools` 사용.

---

## 사용자 입력 처리

공식 문서: https://platform.claude.com/docs/en/agent-sdk/user-input

### canUseTool 콜백

도구 승인 요청과 질문을 처리:

```python
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

async def can_use_tool(tool_name, input_data, context):
    if tool_name == "AskUserQuestion":
        # 질문 처리
        return await handle_questions(input_data)

    # 도구 승인/거부
    if user_approves:
        return PermissionResultAllow(updated_input=input_data)
    else:
        return PermissionResultDeny(message="사용자가 거부")

options = ClaudeAgentOptions(can_use_tool=can_use_tool)
```

### AskUserQuestion 처리

Claude가 사용자에게 질문할 때:

```python
async def handle_questions(input_data):
    answers = {}
    for q in input_data.get("questions", []):
        # 사용자에게 질문 표시하고 답변 수집
        response = await ask_user(q["question"], q["options"])
        answers[q["question"]] = response

    return PermissionResultAllow(
        updated_input={"questions": input_data["questions"], "answers": answers}
    )
```

---

## Hooks

공식 문서: https://platform.claude.com/docs/en/agent-sdk/hooks

에이전트 실행의 주요 시점에서 커스텀 코드 실행:

### 사용 가능한 Hooks

| Hook | Python | TypeScript | 트리거 |
|------|--------|------------|--------|
| PreToolUse | Yes | Yes | 도구 호출 전 (차단/수정 가능) |
| PostToolUse | Yes | Yes | 도구 실행 후 |
| PostToolUseFailure | Yes | Yes | 도구 실행 실패 |
| UserPromptSubmit | Yes | Yes | 프롬프트 제출 |
| Stop | Yes | Yes | 실행 중지 |
| SubagentStart | Yes | Yes | 서브에이전트 시작 |
| SubagentStop | Yes | Yes | 서브에이전트 완료 |
| PreCompact | Yes | Yes | 대화 압축 전 |
| PermissionRequest | Yes | Yes | 권한 요청 |
| Notification | Yes | Yes | 상태 알림 |
| SessionStart | No | Yes | 세션 시작 |
| SessionEnd | No | Yes | 세션 종료 |

### Hook 예시: .env 파일 보호

```python
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

async def protect_env_files(input_data, tool_use_id, context):
    file_path = input_data["tool_input"].get("file_path", "")
    if file_path.endswith(".env"):
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "deny",
                "permissionDecisionReason": ".env 파일 수정 불가",
            }
        }
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [HookMatcher(matcher="Write|Edit", hooks=[protect_env_files])]
    }
)
```

### Hook 출력

- `{}` — 작업 허용 (변경 없음)
- `permissionDecision: "allow"` — 명시적 허용
- `permissionDecision: "deny"` — 차단
- `updatedInput: {...}` — 입력 수정 후 허용 (`permissionDecision: "allow"` 필수)
- `systemMessage: "..."` — 대화에 컨텍스트 주입

deny > ask > allow 우선순위. 여러 Hook 중 하나라도 deny하면 차단.

---

## 서브에이전트

공식 문서: https://platform.claude.com/docs/en/agent-sdk/subagents

### 정의 및 사용

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition

async for message in query(
    prompt="코드 리뷰해줘",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Grep", "Glob", "Agent"],  # Agent 도구 필수
        agents={
            "code-reviewer": AgentDefinition(
                description="코드 품질/보안 리뷰 전문가",
                prompt="코드를 분석하고 개선점을 제안해.",
                tools=["Read", "Grep", "Glob"],  # 읽기 전용
                model="sonnet",  # 모델 오버라이드
            ),
            "test-runner": AgentDefinition(
                description="테스트 실행 및 분석",
                prompt="테스트를 실행하고 결과를 분석해.",
                tools=["Bash", "Read", "Grep"],
            ),
        },
    ),
):
    if hasattr(message, "result"):
        print(message.result)
```

### AgentDefinition 설정

| 필드 | 타입 | 필수 | 설명 |
|:-----|:-----|:-----|:-----|
| description | string | Yes | 언제 사용할지 설명 (Claude가 읽음) |
| prompt | string | Yes | 서브에이전트의 시스템 프롬프트 |
| tools | string[] | No | 사용 가능한 도구. 생략 시 모든 도구 상속 |
| model | string | No | 'sonnet', 'opus', 'haiku', 'inherit' |

주의: 서브에이전트는 자체 서브에이전트를 생성할 수 없음 (Agent를 tools에 포함하지 말 것).

### 서브에이전트가 받는 것

- 자체 시스템 프롬프트 + Agent 도구의 prompt
- CLAUDE.md (settingSources로 로드 시)
- 도구 정의 (부모에서 상속 또는 tools 지정)

**받지 않는 것:** 부모의 대화 이력, 도구 결과, 시스템 프롬프트

---

## 세션 관리

공식 문서: https://platform.claude.com/docs/en/agent-sdk/sessions

### 자동 세션 관리 (ClaudeSDKClient)

```python
async with ClaudeSDKClient(options=options) as client:
    await client.query("Auth 모듈 분석")
    async for message in client.receive_response():
        print(message)

    # 같은 세션 자동 유지
    await client.query("JWT로 리팩토링해줘")
    async for message in client.receive_response():
        print(message)
```

### 세션 ID 캡처 및 재개

```python
session_id = None

async for message in query(prompt="분석해줘", options=options):
    if isinstance(message, ResultMessage):
        session_id = message.session_id

# 나중에 세션 재개
async for message in query(
    prompt="아까 분석한 거 리팩토링해줘",
    options=ClaudeAgentOptions(resume=session_id),
):
    ...
```

### 세션 포크

원본 유지하면서 새 방향 탐색:

```python
async for message in query(
    prompt="OAuth2로 구현해봐",
    options=ClaudeAgentOptions(resume=session_id, fork_session=True),
):
    if isinstance(message, ResultMessage):
        forked_id = message.session_id  # 새 세션 ID

# 원본 세션은 그대로 유지됨
async for message in query(
    prompt="JWT 방식 계속해줘",
    options=ClaudeAgentOptions(resume=session_id),  # 원본
):
    ...
```

### Continue (최근 세션 이어가기)

```python
async for message in query(
    prompt="아까 하던 거 계속해줘",
    options=ClaudeAgentOptions(continue_conversation=True),
):
    ...
```

---

## MCP 연동

공식 문서: https://platform.claude.com/docs/en/agent-sdk/mcp

### MCP 서버 연결

```python
options = ClaudeAgentOptions(
    mcp_servers={
        "github": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {"GITHUB_TOKEN": os.environ["GITHUB_TOKEN"]},
        }
    },
    allowed_tools=["mcp__github__list_issues"],  # mcp__{서버명}__{도구명}
)
```

### 전송 타입

- **stdio**: 로컬 프로세스 (command + args)
- **HTTP/SSE**: 원격 서버 (type: "http" 또는 "sse" + url)
- **SDK MCP**: 인프로세스 커스텀 도구

### 도구 이름 규칙

`mcp__{server_name}__{tool_name}`

와일드카드: `mcp__github__*` (서버의 모든 도구 허용)

---

## 커스텀 도구

공식 문서: https://platform.claude.com/docs/en/agent-sdk/custom-tools

### 도구 정의

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool(
    "get_temperature",
    "현재 기온 조회",
    {"latitude": float, "longitude": float},
)
async def get_temperature(args):
    # API 호출 등
    return {
        "content": [{"type": "text", "text": f"기온: {temp}°C"}]
    }

server = create_sdk_mcp_server(
    name="weather",
    version="1.0.0",
    tools=[get_temperature],
)

# 사용
options = ClaudeAgentOptions(
    mcp_servers={"weather": server},
    allowed_tools=["mcp__weather__get_temperature"],
)
```

### 에러 처리

```python
@tool("fetch_data", "API 데이터 가져오기", {"url": str})
async def fetch_data(args):
    try:
        response = await client.get(args["url"])
        return {"content": [{"type": "text", "text": response.text}]}
    except Exception as e:
        # is_error=True로 반환하면 에이전트 루프 계속됨
        return {
            "content": [{"type": "text", "text": f"오류: {e}"}],
            "is_error": True,
        }
```

### 도구 어노테이션

```python
@tool(
    "get_temperature",
    "기온 조회",
    {"latitude": float, "longitude": float},
    annotations=ToolAnnotations(readOnlyHint=True),  # 병렬 호출 허용
)
```

---

## 구조화된 출력

공식 문서: https://platform.claude.com/docs/en/agent-sdk/structured-outputs

### JSON Schema로 출력 형식 지정

```python
from pydantic import BaseModel

class FeaturePlan(BaseModel):
    feature_name: str
    summary: str
    steps: list[dict]
    risks: list[str]

async for message in query(
    prompt="다크모드 추가 계획 세워줘",
    options=ClaudeAgentOptions(
        output_format={
            "type": "json_schema",
            "schema": FeaturePlan.model_json_schema(),
        }
    ),
):
    if isinstance(message, ResultMessage) and message.structured_output:
        plan = FeaturePlan.model_validate(message.structured_output)
        print(plan.feature_name, plan.summary)
```

---

## 시스템 프롬프트

공식 문서: https://platform.claude.com/docs/en/agent-sdk/modifying-system-prompts

### 4가지 방법

| 방법 | 지속성 | 기본 도구 | 안전성 |
|------|--------|----------|--------|
| CLAUDE.md | 프로젝트 파일 | 유지 | 유지 |
| Output Styles | 파일 저장 | 유지 | 유지 |
| systemPrompt + append | 세션 | 유지 | 유지 |
| Custom systemPrompt | 세션 | 없음 | 직접 추가 |

### Claude Code 프리셋 사용

```python
options = ClaudeAgentOptions(
    system_prompt={"type": "preset", "preset": "claude_code", "append": "항상 한국어로 답변해."},
    setting_sources=["project"],  # CLAUDE.md 로드
)
```

### 커스텀 시스템 프롬프트

```python
options = ClaudeAgentOptions(
    system_prompt="당신은 Python 전문가입니다. 항상 타입 힌트를 포함하세요."
)
```

---

## Skills

공식 문서: https://platform.claude.com/docs/en/agent-sdk/skills

`.claude/skills/*/SKILL.md` 파일로 정의. Claude가 자동으로 발견 및 실행.

```python
options = ClaudeAgentOptions(
    cwd="/path/to/project",
    setting_sources=["user", "project"],  # 필수: Skills 로드
    allowed_tools=["Skill", "Read", "Write", "Bash"],  # Skill 도구 활성화
)
```

---

## 슬래시 명령어

공식 문서: https://platform.claude.com/docs/en/agent-sdk/slash-commands

```python
# 슬래시 명령어 실행
async for message in query(prompt="/compact", options={"max_turns": 1}):
    if message.type == "result":
        print(message.result)
```

### 커스텀 명령어

`.claude/commands/` 또는 `.claude/skills/`에 마크다운 파일로 정의.

---

## 플러그인

공식 문서: https://platform.claude.com/docs/en/agent-sdk/plugins

```python
options = ClaudeAgentOptions(
    plugins=[
        {"type": "local", "path": "./my-plugin"},
    ]
)
```

플러그인 구조:
```
my-plugin/
├── .claude-plugin/
│   └── plugin.json          # 필수: 매니페스트
├── skills/                   # Skills
├── agents/                   # 서브에이전트
├── hooks/                    # 이벤트 핸들러
└── .mcp.json                # MCP 서버
```

---

## 마이그레이션 가이드

공식 문서: https://platform.claude.com/docs/en/agent-sdk/migration-guide

### Claude Code SDK → Claude Agent SDK

```python
# 이전
from claude_code_sdk import query, ClaudeCodeOptions

# 현재
from claude_agent_sdk import query, ClaudeAgentOptions
```

### 주요 변경사항

1. **패키지명**: `claude-code-sdk` → `claude-agent-sdk`
2. **옵션 클래스**: `ClaudeCodeOptions` → `ClaudeAgentOptions`
3. **시스템 프롬프트**: 기본이 minimal. Claude Code 프리셋 필요 시 명시적으로 설정
4. **설정 소스**: 기본적으로 파일시스템 설정 로드 안 함. `setting_sources` 필요

---

## GitHub 저장소

- Python SDK: https://github.com/anthropics/claude-agent-sdk-python
- TypeScript SDK: https://github.com/anthropics/claude-agent-sdk-typescript
- 예제 에이전트: https://github.com/anthropics/claude-agent-sdk-demos

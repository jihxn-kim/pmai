# Claude Agent SDK 옵션 가이드 — 에이전트 구성 전략

pmai와 daggle-ai-backend 두 프로젝트 분석 기반으로 정리한 Agent SDK 옵션 활용 가이드.

---

## 목차

1. [ClaudeAgentOptions 전체 옵션 맵](#1-claudeagentoptions-전체-옵션-맵)
2. [에이전트 행동 제어 — 3가지 레이어](#2-에이전트-행동-제어--3가지-레이어)
3. [system_prompt — 에이전트의 정체성](#3-system_prompt--에이전트의-정체성)
4. [Skills — 파일 기반 워크플로우](#4-skills--파일-기반-워크플로우)
5. [MCP 서버 — 에이전트에 능력 부여](#5-mcp-서버--에이전트에-능력-부여)
6. [도구 접근 제어 — allowed/disallowed](#6-도구-접근-제어--alloweddisallowed)
7. [권한 시스템 — permission_mode](#7-권한-시스템--permission_mode)
8. [세션 관리 — 대화 연속성](#8-세션-관리--대화-연속성)
9. [Hooks — 실행 시점 개입](#9-hooks--실행-시점-개입)
10. [서브에이전트 — 위임 구조](#10-서브에이전트--위임-구조)
11. [구조화된 출력 — output_format](#11-구조화된-출력--output_format)
12. [setting_sources — 설정 로드 경로](#12-setting_sources--설정-로드-경로)
13. [CLAUDE.md — 프로젝트 지침서](#13-claudemd--프로젝트-지침서)
14. [리소스 제한 — 비용/턴/버퍼](#14-리소스-제한--비용턴버퍼)
15. [실전 패턴 비교 — pmai vs daggle](#15-실전-패턴-비교--pmai-vs-daggle)
16. [에이전트 구성 의사결정 플로우차트](#16-에이전트-구성-의사결정-플로우차트)

---

## 1. ClaudeAgentOptions 전체 옵션 맵

```python
ClaudeAgentOptions(
    # ── 정체성 ──
    system_prompt=...,          # str | dict — 에이전트의 역할/규칙 정의
    model=...,                  # str — claude-opus-4-6, claude-sonnet-4-6 등

    # ── 도구/능력 ──
    allowed_tools=[...],        # list[str] — 사용 가능한 도구 목록
    disallowed_tools=[...],     # list[str] — 차단할 도구 (bypassPermissions에서도 차단)
    mcp_servers={...},          # dict — MCP 서버 연결 설정
    permission_mode=...,        # str — default | acceptEdits | bypassPermissions | plan

    # ── 세션 ──
    resume=...,                 # str — 세션 ID로 이전 대화 이어가기
    fork_session=...,           # bool — resume과 함께, 원본 유지하고 분기
    continue_conversation=...,  # bool — 최근 세션 자동 이어가기

    # ── 설정 로드 ──
    setting_sources=[...],      # list[str] — ["user", "project", "local"]
    cwd=...,                    # str — CLI 작업 디렉토리 (Skills 위치 결정)

    # ── 리소스 제한 ──
    max_turns=...,              # int — tool 호출 라운드트립 제한
    max_budget_usd=...,         # float — USD 비용 제한
    max_buffer_size=...,        # int — JSON 파서 버퍼 제한 (기본 1MB)

    # ── 스트리밍 ──
    include_partial_messages=..., # bool — 토큰 단위 스트리밍
    debug_stderr=...,             # bool — CLI stderr 디버그 출력

    # ── 고급 ──
    hooks={...},                # dict — 실행 시점 개입 콜백
    agents={...},               # dict — 서브에이전트 정의
    can_use_tool=...,           # callable — 도구 승인/거부 콜백
    output_format={...},        # dict — JSON Schema 구조화 출력
    env={...},                  # dict — 환경변수 전달
    plugins=[...],              # list — 플러그인 로드
)
```

---

## 2. 에이전트 행동 제어 — 3가지 레이어

에이전트의 행동은 3개의 독립 레이어로 제어된다. 각 레이어는 다른 관점에서 에이전트를 구속한다.

```
┌───────────────────────────────────────────────────────────────┐
│  Layer 1: "무엇을 알고 있는가" (Knowledge)                     │
│                                                               │
│  system_prompt  — 런타임 주입, 세션 단위                       │
│  Skills         — 파일 기반, 프로젝트 단위                     │
│  CLAUDE.md      — 프로젝트 지침서, 자동 로드                   │
│                                                               │
│  → 에이전트의 역할, 규칙, 워크플로우를 정의                     │
├───────────────────────────────────────────────────────────────┤
│  Layer 2: "무엇을 할 수 있는가" (Capability)                   │
│                                                               │
│  mcp_servers     — 외부 시스템 연결 (GitHub, DB, 브라우저 등)  │
│  allowed_tools   — 접근 가능한 도구 화이트리스트                │
│  disallowed_tools — 절대 차단 블랙리스트                       │
│  permission_mode — 도구 실행 권한 수준                         │
│                                                               │
│  → 에이전트가 사용할 수 있는 도구와 API를 제한                  │
├───────────────────────────────────────────────────────────────┤
│  Layer 3: "어떻게 실행되는가" (Execution)                      │
│                                                               │
│  max_turns       — 루프 횟수 제한                              │
│  max_budget_usd  — 비용 상한                                  │
│  resume          — 세션 연속성                                 │
│  hooks           — 실행 중 개입                                │
│  output_format   — 출력 구조 강제                              │
│                                                               │
│  → 에이전트의 실행 범위와 형태를 제어                           │
└───────────────────────────────────────────────────────────────┘
```

---

## 3. system_prompt — 에이전트의 정체성

에이전트에게 "너는 누구이고 어떻게 행동해라"를 알려주는 가장 기본적인 방법.

### 3가지 사용 방식

```python
# 방식 1: 완전 커스텀 — 기본 도구 설명 없음, 직접 정의
options = ClaudeAgentOptions(
    system_prompt="당신은 코드 리뷰 전문가입니다. 보안, 성능, 유지보수성을 중점으로 검토하세요."
)

# 방식 2: Claude Code 프리셋 + 추가 지시 — 기본 도구 설명 유지
options = ClaudeAgentOptions(
    system_prompt={
        "type": "preset",
        "preset": "claude_code",
        "append": "항상 한국어로 답변해. PM Agent 역할로 프로젝트 관리 관점에서 분석해."
    }
)

# 방식 3: system_prompt 없이 Skills/CLAUDE.md에 위임
options = ClaudeAgentOptions(
    setting_sources=["project"],  # CLAUDE.md + Skills 로드
    cwd="/path/to/project",       # .claude/ 디렉토리 위치
    # system_prompt 생략
)
```

### 실전 비교

| 프로젝트 | 방식 | 특징 |
|----------|------|------|
| **pmai** | 방식 1 (커스텀 문자열) | 용도별 프롬프트 5개를 `prompts.py`에 하드코딩 |
| **daggle** | 방식 1 + Skills 병행 | 가벼운 system_prompt + 상세 규칙은 Skills에 분리 |

### 언제 뭘 쓰나

| 상황 | 추천 방식 |
|------|----------|
| 단일 목적 에이전트 (코드리뷰, 분석 등) | 커스텀 문자열로 충분 |
| 다단계 워크플로우 (PRD → FRD → 디자인) | Skills로 단계별 분리 |
| Read/Grep 등 기본 도구 설명이 필요 | preset + append |
| 대화형 범용 에이전트 | preset + append + CLAUDE.md |

---

## 4. Skills — 파일 기반 워크플로우

`.claude/skills/<skill-name>/SKILL.md` 파일로 정의하는 재사용 가능한 워크플로우.
Claude가 자동 발견하여 `Skill` 도구로 실행.

### 구조

```
.claude/
└── skills/
    ├── phase-1-prd/
    │   └── SKILL.md        ← YAML frontmatter + 마크다운 본문
    ├── phase-2-frd/
    │   └── SKILL.md
    └── phase-3-design/
        └── SKILL.md
```

### SKILL.md 형식 (daggle 예시)

```markdown
---
name: phase-1-prd
description: PRD 생성 워크플로우 — 체크리스트 기반 정보 수집 후 save_prd 호출
---

## 워크플로우

1. 사용자 요구사항 수집 (대화형)
2. 체크리스트 항목 확인
3. `save_prd` 도구로 PRD 문서 생성

## 출력 스키마

(상세 필드 정의...)

## 품질 기준

(검증 규칙...)
```

### Skills가 필요한 조건

```python
# setting_sources에 "project" 포함 필수
# cwd가 .claude/skills/ 를 포함하는 프로젝트 루트를 가리켜야 함
# allowed_tools에 "Skill" 포함 필수
options = ClaudeAgentOptions(
    setting_sources=["project"],
    cwd="/path/to/project",
    allowed_tools=["Skill", "mcp__daggle__*"],
)
```

### system_prompt vs Skills 비교

| 관점 | system_prompt | Skills |
|------|---------------|--------|
| 정의 위치 | 코드 내 문자열 | `.claude/skills/*/SKILL.md` 파일 |
| 변경 시 | 코드 배포 필요 | 파일 수정만으로 반영 |
| 길이 제한 | context window 제약 | Claude가 필요할 때만 로드 |
| 다단계 워크플로우 | 하나의 긴 프롬프트 | 단계별 스킬 분리 |
| 사용 시점 | 항상 로드 | Claude가 관련성 판단 후 선택 로드 |
| 적합한 경우 | 짧은 역할 정의 | 복잡한 절차/체크리스트 |

### pmai에서 Skills 도입 시

현재 `prompts.py`의 5개 프롬프트를 Skills로 분리 가능:

```
.claude/skills/
├── code-review/SKILL.md      ← CODE_REVIEWER_PROMPT
├── project-analysis/SKILL.md ← PROJECT_ANALYST_PROMPT + 출력 스키마
├── test-generation/SKILL.md  ← TEST_GENERATOR_PROMPT
├── qa-flow/SKILL.md          ← QA_FLOW_PROMPT
└── weekly-briefing/SKILL.md  ← WEEKLY_BRIEFING_PROMPT
```

장점: 프롬프트 수정 시 코드 배포 없이 파일만 수정. 단, `setting_sources=["project"]`와 `cwd` 설정 필요.

---

## 5. MCP 서버 — 에이전트에 능력 부여

MCP(Model Context Protocol) 서버는 에이전트에게 외부 시스템 접근 능력을 부여한다.

### 3가지 전송 방식

```python
mcp_servers = {
    # 1. stdio — 로컬 subprocess (가장 일반적)
    "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_TOKEN": token},
    },

    # 2. HTTP/SSE — 원격 서버
    "remote": {
        "type": "http",
        "url": "https://mcp.example.com/sse",
    },

    # 3. SDK MCP — 인프로세스 (Python 함수를 도구로 노출)
    "custom": create_sdk_mcp_server(
        name="custom", version="1.0.0", tools=[my_tool],
    ),
}
```

### 실전 비교

| MCP 서버 | pmai | daggle | 방식 |
|----------|------|--------|------|
| GitHub | `npx server-github` | - | stdio |
| PM Agent DB | `python -m pm_mcp_server` | - | stdio (custom) |
| Playwright | `npx @playwright/mcp` | - | stdio |
| Daggle 기능 도구 | - | `python -m mcp_server` | stdio (custom) |

### Custom MCP 서버 설계 패턴

두 프로젝트 모두 **별도 Python 프로세스를 stdio MCP로 실행**하는 패턴을 사용:

```python
# executor에서 MCP 서버 설정
mcp_servers["pm_agent"] = {
    "command": sys.executable,
    "args": ["-m", "app.services.ai.pm_mcp_server", org_id],
    "env": {"DATABASE_URL": settings.database_url},
}

# pm_mcp_server.py — 별도 프로세스로 실행됨
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("pm-agent")

@server.list_tools()
async def list_tools():
    return [types.Tool(name="get_project_tasks", ...)]

@server.call_tool()
async def call_tool(name, arguments):
    result = await execute_db_query(name, ...)
    return [types.TextContent(type="text", text=json.dumps(result))]

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, ...)
```

### SDK MCP vs stdio MCP 선택 기준

| 관점 | SDK MCP (인프로세스) | stdio MCP (서브프로세스) |
|------|---------------------|------------------------|
| 설정 복잡도 | 간단 (`@tool` 데코레이터) | 별도 서버 코드 필요 |
| DB 접근 | 부모 프로세스와 공유 | 별도 DB 연결 필요 |
| 격리 | 없음 (같은 프로세스) | 완전 격리 |
| 스트리밍 호환 | `include_partial_messages`와 충돌 가능 | 문제 없음 |
| 디버깅 | 부모 로그와 섞임 | 독립 stderr |
| 추천 | 간단한 도구 1-2개 | DB 접근, 복잡한 도구, 프로덕션 |

> **주의**: SDK MCP + `include_partial_messages=True` 조합은 백프레셔 데드락 발생 가능 (Issue #425). 프로덕션에서는 stdio MCP 사용 권장.

---

## 6. 도구 접근 제어 — allowed/disallowed

### allowed_tools — 화이트리스트

```python
# 특정 도구만 허용
allowed_tools=["Read", "Glob", "Grep"]

# MCP 서버의 모든 도구 허용 (와일드카드)
allowed_tools=["mcp__github__*", "mcp__pm_agent__*"]

# 내장 도구 + MCP + Skills 조합
allowed_tools=["Read", "Glob", "Grep", "Bash", "Skill", "mcp__daggle__*"]
```

### disallowed_tools — 블랙리스트 (bypassPermissions에서도 차단)

```python
# Bash 실행 절대 차단 (bypassPermissions에서도)
disallowed_tools=["Bash"]

# 파일 수정 차단 (읽기 전용 에이전트)
disallowed_tools=["Write", "Edit"]
```

### 도구 접근 제어 전략 비교

| 전략 | 설명 | 예시 |
|------|------|------|
| **최소 권한** | 필요한 도구만 명시 | 코드리뷰: `["Read", "Grep", "mcp__github__*"]` |
| **단계별 확장** (daggle) | phase에 따라 도구 추가 | phase 1: `save_prd`만, phase 5: 전체 |
| **전체 허용** (pmai) | bypass + 와일드카드 | `bypassPermissions` + `mcp__*` |
| **블랙리스트** | 위험한 것만 차단 | `disallowed_tools=["Bash"]` |

### daggle의 단계별 도구 확장 패턴

```python
# phase_config.py
_PHASE_FEATURE_TOOLS = {
    1: ["save_prd"],
    2: ["save_prd", "save_frd"],
    3: ["save_prd", "save_frd", "save_design_system",
        "load_design_reference", "render_wireframe"],
    4: [... + "render_gui"],
    5: [... + "build_code"],
}

# 항상 사용 가능한 기본 도구
_DATA_TOOLS = ["get_data", "save_data"]

# options.py
allowed = [f"mcp__daggle__{t}" for t in _DATA_TOOLS + _PHASE_FEATURE_TOOLS[phase]]
allowed.append("Skill")  # Skills 항상 허용
```

이 패턴은 에이전트가 현재 단계에 해당하지 않는 도구를 호출하는 걸 **구조적으로 차단**한다.

---

## 7. 권한 시스템 — permission_mode

### 모드 비교

| Mode | 동작 | 용도 |
|------|------|------|
| `default` | 미승인 도구 → `can_use_tool` 콜백 호출 | 사용자 승인 필요한 인터랙티브 앱 |
| `acceptEdits` | 파일 수정 자동 승인, 나머지는 콜백 | 코딩 에이전트 |
| `bypassPermissions` | 모든 도구 자동 승인 | 서버 자동화 (pmai, daggle 모두 사용) |
| `plan` | 도구 실행 없음, 분석/계획만 | 검토 단계, dry-run |

### 실전: 서버 환경에서는 거의 항상 bypassPermissions

두 프로젝트 모두 `bypassPermissions` 사용. 사용자 승인 UI가 없는 서버 환경에서는 사실상 유일한 선택.

```python
# 서버 자동화에서의 표준 패턴
options = ClaudeAgentOptions(
    permission_mode="bypassPermissions",
    allowed_tools=[...],          # 화이트리스트로 범위 제한
    disallowed_tools=["Bash"],    # 위험한 도구는 블랙리스트로 차단
)
```

### can_use_tool 콜백 — 동적 승인

```python
async def can_use_tool(tool_name, input_data, context):
    if tool_name == "AskUserQuestion":
        # 에이전트의 질문을 사용자에게 전달
        answer = await forward_to_user(input_data)
        return PermissionResultAllow(updated_input={...})

    if tool_name == "Bash" and "rm" in input_data.get("command", ""):
        return PermissionResultDeny(message="삭제 명령 불허")

    return PermissionResultAllow(updated_input=input_data)
```

---

## 8. 세션 관리 — 대화 연속성

### resume — 이전 세션 이어가기

```python
# 1. 첫 대화 — 세션 ID 캡처
session_id = None
async for msg in query(prompt="분석해줘", options=options):
    if isinstance(msg, SystemMessage):
        session_id = msg.session_id
    elif isinstance(msg, ResultMessage):
        session_id = msg.session_id

# 2. 이후 대화 — 세션 재개
options_with_resume = ClaudeAgentOptions(
    resume=session_id,     # system_prompt 대신 resume 사용
    allowed_tools=[...],
    mcp_servers={...},
)
async for msg in query(prompt="아까 거 리팩토링해줘", options=options_with_resume):
    ...
```

### 세션 저장소 패턴 비교

| 프로젝트 | 저장소 | 키 | 수명 |
|----------|--------|-----|------|
| **pmai** | 인메모리 dict | Slack channel_id | 컨테이너 재시작 시 소멸 |
| **daggle** | PostgreSQL | user_id\|project_id\|conversation_id | 영구 |

### pmai Slack 세션 패턴

```python
_channel_sessions: dict[str, str] = {}  # channel_id → session_id

# 세션이 있으면 resume, 없으면 system_prompt
if channel in _channel_sessions:
    options = ClaudeAgentOptions(resume=_channel_sessions[channel], ...)
else:
    options = ClaudeAgentOptions(system_prompt=SLACK_BOT_PROMPT, ...)

# 호출 후 세션 저장
_channel_sessions[channel] = captured_session_id
```

### 주의: resume 사용 시 system_prompt는 무시됨

```python
# resume와 system_prompt를 동시에 설정하면 resume 우선
# 새 세션 → system_prompt 설정
# 기존 세션 → resume만 설정 (system_prompt 생략)

if existing_session_id:
    opts = ClaudeAgentOptions(resume=existing_session_id)
else:
    opts = ClaudeAgentOptions(system_prompt="...")
```

### fork_session — 원본 유지하고 분기

```python
# A/B 테스트, 대안 탐색에 유용
options = ClaudeAgentOptions(
    resume=session_id,
    fork_session=True,  # 원본 세션 유지, 새 분기 생성
)
```

---

## 9. Hooks — 실행 시점 개입

### 사용 가능한 Hook 종류

| Hook | 트리거 | 용도 |
|------|--------|------|
| PreToolUse | 도구 호출 전 | 차단/수정/로깅 |
| PostToolUse | 도구 실행 후 | 결과 검증/로깅 |
| Stop | 실행 중지 시 | 정리 작업 |
| SubagentStart/Stop | 서브에이전트 시작/완료 | 모니터링 |
| PreCompact | 대화 압축 전 | 중요 정보 보존 |
| Notification | 상태 알림 | 진행률 추적 |

### 예시: 민감 파일 보호

```python
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

async def protect_sensitive_files(input_data, tool_use_id, context):
    file_path = input_data["tool_input"].get("file_path", "")
    if any(p in file_path for p in [".env", "credentials", "secret"]):
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "deny",
                "permissionDecisionReason": "민감 파일 접근 불가",
            }
        }
    return {}

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Write|Edit|Read", hooks=[protect_sensitive_files])
        ]
    }
)
```

### 실전: 두 프로젝트 모두 Hooks 미사용

- **pmai**: 사용 안 함
- **daggle**: 초기에 Hook으로 도구 제한 시도 → `allowed_tools`로 전환 (더 간단)

```python
# daggle hooks.py
"""Hooks are no longer used — phase restriction is enforced via
allowed_tools in ClaudeAgentOptions."""
```

**결론**: 단순 도구 제한은 `allowed_tools`로, 조건부 로직(파일 경로 검사 등)이 필요할 때만 Hooks 사용.

---

## 10. 서브에이전트 — 위임 구조

### 정의 및 사용

```python
from claude_agent_sdk import AgentDefinition

options = ClaudeAgentOptions(
    allowed_tools=["Read", "Grep", "Agent"],  # Agent 도구 필수
    agents={
        "code-reviewer": AgentDefinition(
            description="코드 품질/보안 리뷰 전문가",
            prompt="코드를 분석하고 개선점을 제안해.",
            tools=["Read", "Grep", "Glob"],  # 읽기 전용
            model="sonnet",
        ),
        "test-writer": AgentDefinition(
            description="테스트 케이스 생성 전문가",
            prompt="테스트를 작성해.",
            tools=["Read", "Write", "Bash"],
            model="haiku",  # 비용 절감
        ),
    },
)
```

### 서브에이전트 제약

- 자체 서브에이전트 생성 불가 (1단계 깊이만)
- 부모의 대화 이력 상속 안 됨
- 부모의 system_prompt 상속 안 됨
- Agent 도구의 prompt만 전달받음

### 실전: 두 프로젝트 모두 서브에이전트 미사용

- **pmai**: 용도별로 별도 `query()` 호출 (run_code_review, run_project_analysis 등)
- **daggle**: 단일 `query()` 호출, phase별 Skills로 행동 분리

서브에이전트 대신 **용도별 query()를 분리 호출**하는 게 현재 두 프로젝트의 패턴.

---

## 11. 구조화된 출력 — output_format

### JSON Schema로 출력 강제

```python
from pydantic import BaseModel

class AnalysisResult(BaseModel):
    summary: str
    issues: list[dict]
    score: float

options = ClaudeAgentOptions(
    output_format={
        "type": "json_schema",
        "schema": AnalysisResult.model_json_schema(),
    }
)

async for msg in query(prompt="분석해줘", options=options):
    if isinstance(msg, ResultMessage) and msg.structured_output:
        result = AnalysisResult.model_validate(msg.structured_output)
```

### 제한사항

- 스트리밍 중에는 접근 불가, `ResultMessage.structured_output`에서만 제공
- extended thinking과 함께 사용 시 제약 있음

### 실전: 두 프로젝트 모두 미사용

대신 **프롬프트 내 출력 형식 지시 + 후처리 파싱**으로 구현:

```python
# pmai — 프롬프트에 JSON 블록 형식 지시
PROJECT_ANALYST_PROMPT = """
...
보고서 끝에 다음 형식으로 이슈를 추가해:
```json:issues
[{"title": "...", "severity": "...", ...}]
```
"""

# 후처리에서 파싱
if "json:issues" in result_text:
    issues_json = extract_json_block(result_text, "issues")
```

---

## 12. setting_sources — 설정 로드 경로

### 옵션 값

| 값 | 로드 대상 | 경로 |
|----|----------|------|
| `"user"` | 사용자 전역 설정 | `~/.claude/settings.json` |
| `"project"` | 프로젝트 설정 + CLAUDE.md + Skills | `.claude/` 디렉토리 |
| `"local"` | 로컬 오버라이드 | `.claude.local/` |

### 핵심: Skills를 사용하려면 반드시 `"project"` 포함

```python
# Skills 로드 O
options = ClaudeAgentOptions(
    setting_sources=["project"],
    cwd="/path/to/project",  # .claude/skills/ 가 여기 아래에 있어야 함
)

# Skills 로드 X — setting_sources 생략 시 파일시스템 설정 안 읽음
options = ClaudeAgentOptions(
    # setting_sources 미설정 → Skills, CLAUDE.md 모두 무시
)
```

### 실전 비교

| 프로젝트 | setting_sources | Skills 사용 | CLAUDE.md |
|----------|-----------------|-------------|-----------|
| **pmai** | 미설정 | X | X |
| **daggle** | `["project"]` | O (5개 phase 스킬) | X |

---

## 13. CLAUDE.md — 프로젝트 지침서

프로젝트 루트의 `CLAUDE.md` 파일. `setting_sources=["project"]` 설정 시 자동 로드.

### 용도

- 코딩 컨벤션, 아키텍처 규칙
- 프로젝트 특화 지침 (예: "이 프로젝트는 한국어로 커밋 메시지 작성")
- 반복적으로 적용되는 규칙 (system_prompt보다 적합)

### system_prompt vs CLAUDE.md vs Skills

| 관점 | system_prompt | CLAUDE.md | Skills |
|------|---------------|-----------|--------|
| 적용 범위 | 해당 세션만 | 프로젝트 전체 | 관련 작업만 |
| 로드 시점 | 항상 | 자동 (setting_sources) | Claude 판단 후 선택 |
| 변경 | 코드 수정 필요 | 파일 수정 | 파일 수정 |
| 크기 | context 소비 | context 소비 | 필요 시만 로드 |
| 용도 | 역할 정의 | 프로젝트 규칙 | 워크플로우 절차 |

---

## 14. 리소스 제한 — 비용/턴/버퍼

### max_turns

```python
# 용도별 적정 값
max_turns=1    # 단발성 분류/파싱 (pmai parse_intent)
max_turns=10   # 짧은 대화 (pmai Slack)
max_turns=20   # 일반 분석 (pmai 기본값)
max_turns=50   # 복잡한 멀티스텝 (pmai QA flow, daggle 전체)
```

### max_budget_usd

```python
# daggle만 사용
max_budget_usd=10.0  # 쿼리당 $10 상한
```

### max_buffer_size

```python
# Playwright 스크린샷 등 대용량 MCP 응답 시 필수
max_buffer_size=10 * 1024 * 1024  # 10MB (기본값 1MB)
```

---

## 15. 실전 패턴 비교 — pmai vs daggle

### 아키텍처 차이

```
┌─────────────────────────────────────────────────────────────┐
│                          pmai                                │
│                                                             │
│  "용도별 에이전트 분리" 패턴                                  │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │코드리뷰   │ │프로젝트   │ │QA 테스트  │ │Slack 봇  │       │
│  │에이전트   │ │분석 에이전│ │에이전트   │ │에이전트   │       │
│  │          │ │트        │ │          │ │          │       │
│  │prompt:   │ │prompt:   │ │prompt:   │ │prompt:   │       │
│  │코드리뷰  │ │분석      │ │QA        │ │Slack PM  │       │
│  │          │ │          │ │          │ │          │       │
│  │turns:20  │ │turns:20  │ │turns:50  │ │turns:10  │       │
│  │          │ │          │ │          │ │resume:O  │       │
│  │MCP:      │ │MCP:      │ │MCP:      │ │MCP:      │       │
│  │ github   │ │ github   │ │playwright│ │ pm_agent │       │
│  │          │ │ pm_agent │ │ github   │ │ github   │       │
│  │          │ │          │ │ pm_agent │ │          │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                             │
│  특징:                                                      │
│  - system_prompt를 prompts.py에 하드코딩                     │
│  - Skills/CLAUDE.md 미사용                                  │
│  - 세션은 Slack 채널 단위로만 유지                            │
│  - setting_sources 미설정                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        daggle                                │
│                                                             │
│  "단일 에이전트 + 단계별 도구 확장" 패턴                      │
│                                                             │
│            ┌────────────────────────┐                        │
│            │   단일 에이전트         │                        │
│            │                        │                        │
│            │   system_prompt: 가벼운 │                        │
│            │   역할 정의             │                        │
│            │                        │                        │
│            │   Skills: phase별      │                        │
│            │   워크플로우 자동 로드   │                        │
│            │                        │                        │
│            │   setting_sources:     │                        │
│            │     ["project"]        │                        │
│            └───────────┬────────────┘                        │
│                        │                                    │
│        ┌───────┬───────┼───────┬───────┐                    │
│        ▼       ▼       ▼       ▼       ▼                    │
│     Phase1  Phase2  Phase3  Phase4  Phase5                  │
│     save_   save_   design  render  build_                  │
│     prd     frd     +wire   _gui    code                    │
│                     frame                                   │
│                                                             │
│  특징:                                                      │
│  - system_prompt은 최소한 + Skills에 상세 규칙 위임           │
│  - 단계마다 allowed_tools가 확장됨                           │
│  - 세션을 DB에 영구 저장 (resume)                            │
│  - model도 단계별로 변경 (sonnet → opus)                     │
│  - max_budget_usd 설정으로 비용 관리                         │
└─────────────────────────────────────────────────────────────┘
```

### 옵션 사용 비교표

| 옵션 | pmai | daggle |
|------|------|--------|
| system_prompt | 하드코딩 (5종) | 가벼운 역할 정의 |
| Skills | X | O (5개 phase 스킬) |
| CLAUDE.md | X | X |
| setting_sources | X | `["project"]` |
| MCP 서버 | GitHub + PM Agent + Playwright | daggle (custom 1개) |
| MCP 방식 | stdio (3개 별도 프로세스) | stdio (1개 통합 프로세스) |
| allowed_tools | 용도별 고정 | 단계별 동적 확장 |
| disallowed_tools | X | X |
| permission_mode | bypassPermissions | bypassPermissions |
| resume | Slack만 (인메모리) | 전체 (DB 영구) |
| max_turns | 1/10/20/50 (용도별) | 50 (통일) |
| max_budget_usd | X | $10 |
| max_buffer_size | 10MB | 미설정 |
| hooks | X | X (폐기) |
| agents (서브에이전트) | X | X |
| output_format | X | X |
| model | opus 고정 | 단계별 (sonnet/opus) |
| can_use_tool | X | X |
| env | DATABASE_URL 전달 | 전체 환경변수 전달 |
| cwd | 조건부 | 프로젝트 루트 고정 |
| debug_stderr | O | O |
| include_partial_messages | O | O |

---

## 16. 에이전트 구성 의사결정 플로우차트

새 에이전트를 만들 때 어떤 옵션을 선택할지 결정하는 가이드.

```
에이전트 구성 시작
    │
    ├─ Q: 서버 자동화인가, 사용자 인터랙티브인가?
    │     │
    │     ├─ 서버 → permission_mode: "bypassPermissions"
    │     └─ 인터랙티브 → permission_mode: "default" + can_use_tool 구현
    │
    ├─ Q: 외부 시스템 접근이 필요한가?
    │     │
    │     ├─ GitHub → mcp_servers에 server-github 추가
    │     ├─ DB 조회 → custom stdio MCP 서버 구현
    │     ├─ 브라우저 → Playwright MCP 추가 + max_buffer_size=10MB
    │     └─ 없음 → mcp_servers 생략
    │
    ├─ Q: 워크플로우가 복잡한가?
    │     │
    │     ├─ 단순 (코드리뷰, 분류) → system_prompt만으로 충분
    │     ├─ 복잡한 단일 워크플로우 → system_prompt에 상세 지시
    │     └─ 다단계 워크플로우 → Skills 분리 + setting_sources=["project"]
    │
    ├─ Q: 대화 연속성이 필요한가?
    │     │
    │     ├─ 일회성 → resume 불필요
    │     ├─ 채팅 세션 → resume + 세션 저장소 구현
    │     └─ 분기 탐색 → fork_session
    │
    ├─ Q: 도구 접근을 제한해야 하는가?
    │     │
    │     ├─ 읽기 전용 → allowed_tools=["Read", "Glob", "Grep"]
    │     ├─ 단계별 확장 → phase_config 패턴 (daggle)
    │     ├─ 특정 차단 → disallowed_tools=["Bash"]
    │     └─ 전체 허용 → 와일드카드 "mcp__*"
    │
    ├─ Q: 비용 관리가 중요한가?
    │     │
    │     ├─ 예 → max_budget_usd 설정 + model 단계별 선택 (haiku/sonnet/opus)
    │     └─ 아니오 → 생략
    │
    └─ Q: 출력 형식이 고정되어야 하는가?
          │
          ├─ 정형 데이터 필요 → output_format + Pydantic 모델
          ├─ 유연한 형식 → 프롬프트에 형식 지시 + 후처리 파싱
          └─ 자유 텍스트 → 생략
```

### 최소 구성 예시

```python
# 가장 간단한 에이전트 — 읽기 전용 분석
options = ClaudeAgentOptions(
    system_prompt="프로젝트를 분석하고 보고서를 작성해.",
    allowed_tools=["Read", "Glob", "Grep"],
    permission_mode="bypassPermissions",
    max_turns=20,
)
```

### 풀 스택 구성 예시

```python
# 모든 옵션을 활용하는 에이전트
options = ClaudeAgentOptions(
    # 정체성
    system_prompt={"type": "preset", "preset": "claude_code", "append": "PM Agent 역할"},
    model="claude-opus-4-6",

    # 도구/능력
    mcp_servers={
        "pm_agent": pm_mcp_config,
        "github": github_mcp_config,
    },
    allowed_tools=["Read", "Glob", "Grep", "Skill", "mcp__pm_agent__*", "mcp__github__*"],
    disallowed_tools=["Bash"],
    permission_mode="bypassPermissions",

    # 설정 로드
    setting_sources=["project"],
    cwd="/path/to/project",

    # 세션
    resume=previous_session_id,

    # 리소스
    max_turns=50,
    max_budget_usd=10.0,
    max_buffer_size=10 * 1024 * 1024,

    # 스트리밍
    include_partial_messages=True,
    debug_stderr=True,

    # 환경
    env={"DATABASE_URL": db_url},
)
```

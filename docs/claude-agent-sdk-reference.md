# Claude Agent SDK Reference

Claude Agent SDK의 전체 API 레퍼런스 + pmai/daggle 실전 패턴 가이드 통합 문서.
공식 문서: https://platform.claude.com/docs/en/agent-sdk

---

## 목차

1. [설치 및 기본 사용](#1-설치-및-기본-사용)
2. [ClaudeAgentOptions 전체 옵션 맵](#2-claudeagentoptions-전체-옵션-맵)
3. [에이전트 행동 제어 — 3가지 레이어](#3-에이전트-행동-제어--3가지-레이어)
4. [시스템 프롬프트](#4-시스템-프롬프트)
5. [Skills](#5-skills--파일-기반-워크플로우)
6. [CLAUDE.md + setting_sources](#6-claudemd--setting_sources)
7. [MCP 서버](#7-mcp-서버)
8. [커스텀 도구](#8-커스텀-도구)
9. [도구 접근 제어](#9-도구-접근-제어--alloweddisallowed)
10. [권한 시스템](#10-권한-시스템--permission_mode)
11. [사용자 입력 처리](#11-사용자-입력-처리)
12. [Hooks](#12-hooks)
13. [서브에이전트](#13-서브에이전트)
14. [세션 관리](#14-세션-관리)
15. [메시지 타입](#15-메시지-타입)
16. [스트리밍 출력](#16-스트리밍-출력)
17. [토큰 사용량 및 과금](#17-토큰-사용량-및-과금)
18. [구조화된 출력](#18-구조화된-출력)
19. [리소스 제한](#19-리소스-제한--비용턴버퍼)
20. [입력 모드](#20-입력-모드)
21. [슬래시 명령어](#21-슬래시-명령어)
22. [플러그인](#22-플러그인)
23. [Playwright MCP 트러블슈팅](#23-playwright-mcp-트러블슈팅)
24. [알려진 제한사항](#24-알려진-제한사항)
25. [실전 패턴 비교 — pmai vs daggle](#25-실전-패턴-비교--pmai-vs-daggle)
26. [에이전트 구성 의사결정 플로우차트](#26-에이전트-구성-의사결정-플로우차트)
27. [마이그레이션 가이드](#27-마이그레이션-가이드)
28. [GitHub 저장소](#28-github-저장소)

---

## 1. 설치 및 기본 사용

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

## 2. ClaudeAgentOptions 전체 옵션 맵

### 파라미터 레퍼런스

| 파라미터 | 타입 | 용도 |
|---------|------|------|
| system_prompt | str 또는 dict | 시스템 프롬프트 (문자열 또는 `{"type": "preset", "preset": "claude_code", "append": "..."}`) |
| model | str | 모델 선택 (claude-sonnet-4-6, claude-opus-4-6 등) |
| allowed_tools | list[str] | 허용 tool 목록 (와일드카드 가능: `mcp__github__*`) |
| disallowed_tools | list[str] | 차단 tool 목록 (bypassPermissions에서도 차단) |
| permission_mode | str | default / acceptEdits / bypassPermissions / plan / dontAsk(TS only) |
| max_turns | int | tool 호출 라운드트립 제한 |
| max_budget_usd | float | 비용 제한 (USD). 초과 시 에이전트 중단 |
| include_partial_messages | bool | StreamEvent 토큰 단위 스트리밍 활성화. SDK MCP와 함께 사용 시 백프레셔 주의 (Issue #425) |
| debug_stderr | bool | CLI subprocess의 stderr 출력을 포함. MCP 서버 시작 실패 등 디버깅에 필수 |
| mcp_servers | dict | MCP 서버 설정. stdio: `{"command": "...", "args": [...], "env": {...}}`, SDK MCP: `create_sdk_mcp_server()` 결과 |
| setting_sources | list[str] | 설정 로드 소스. `["user"]`, `["project"]`, `["local"]` 조합. 생략 시 파일시스템 설정 안 읽음. `"project"` 포함해야 CLAUDE.md/Skills 로드 |
| cwd | str | CLI subprocess의 작업 디렉토리 |
| env | dict | CLI subprocess에 전달할 환경변수. 주의: setting_sources로 로드된 settings.json의 env와 충돌 가능 (Issue #217, SDK >= 0.1.50에서 수정) |
| resume | str | 세션 ID로 이전 대화 이어가기. 세션 파일이 디스크에 있어야 함 |
| continue_conversation | bool | 가장 최근 세션 자동 이어가기 |
| fork_session | bool | resume과 함께 사용. 원본 유지하면서 새 분기 생성 |
| hooks | dict | PreToolUse/PostToolUse/Stop 등 hook 콜백 등록 |
| agents | dict | 서브에이전트 정의 (AgentDefinition) |
| can_use_tool | callable | tool 승인/거부 콜백 |
| output_format | dict | 구조화된 JSON 출력 (`{"type": "json_schema", "schema": {...}}`) |
| max_buffer_size | int | CLI stdout JSON 파서 버퍼 제한 (기본 1MB). Playwright 스크린샷 등 대용량 MCP 응답 시 `10 * 1024 * 1024` (10MB)로 설정 필요 (Issue [#98](https://github.com/anthropics/claude-agent-sdk-python/issues/98)) |
| plugins | list | 플러그인 로드 (`{"type": "local", "path": "..."}`) |

### 카테고리별 분류

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

## 3. 에이전트 행동 제어 — 3가지 레이어

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

## 4. 시스템 프롬프트

공식 문서: https://platform.claude.com/docs/en/agent-sdk/modifying-system-prompts

### 4가지 방법

| 방법 | 지속성 | 기본 도구 | 안전성 |
|------|--------|----------|--------|
| CLAUDE.md | 프로젝트 파일 | 유지 | 유지 |
| Output Styles | 파일 저장 | 유지 | 유지 |
| systemPrompt + append | 세션 | 유지 | 유지 |
| Custom systemPrompt | 세션 | 없음 | 직접 추가 |

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
    },
    setting_sources=["project"],  # CLAUDE.md 로드
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

## 5. Skills — 파일 기반 워크플로우

공식 문서: https://platform.claude.com/docs/en/agent-sdk/skills

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

## 6. CLAUDE.md + setting_sources

### setting_sources 옵션

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

### CLAUDE.md 용도

프로젝트 루트의 `CLAUDE.md` 파일. `setting_sources=["project"]` 설정 시 자동 로드.

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

### 실전 비교

| 프로젝트 | setting_sources | Skills 사용 | CLAUDE.md |
|----------|-----------------|-------------|-----------|
| **pmai** | 미설정 | X | X |
| **daggle** | `["project"]` | O (5개 phase 스킬) | X |

---

## 7. MCP 서버

공식 문서: https://platform.claude.com/docs/en/agent-sdk/mcp

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

### 도구 이름 규칙

`mcp__{server_name}__{tool_name}`

와일드카드: `mcp__github__*` (서버의 모든 도구 허용)

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

## 8. 커스텀 도구

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

## 9. 도구 접근 제어 — allowed/disallowed

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

### allowed_tools vs disallowed_tools

`allowed_tools`는 `bypassPermissions` 모드에서 **무시됨** (어차피 전부 승인).
`disallowed_tools`는 `bypassPermissions`에서도 **절대 차단**.

```python
# 이렇게 하면 Bash도 실행됨 (bypassPermissions가 allowed_tools를 무시)
options = ClaudeAgentOptions(
    permission_mode="bypassPermissions",
    allowed_tools=["Read", "Grep"],  # 의미 없음
)

# 이렇게 해야 Bash가 진짜 차단됨
options = ClaudeAgentOptions(
    permission_mode="bypassPermissions",
    disallowed_tools=["Bash"],  # bypassPermissions에서도 차단
)
```

주의: `allowed_tools`는 `bypassPermissions`를 제한하지 않음. 차단하려면 `disallowed_tools` 사용.

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

## 10. 권한 시스템 — permission_mode

공식 문서: https://platform.claude.com/docs/en/agent-sdk/permissions

### 5가지 모드

| Mode | 동작 | Python | TS | 용도 |
|------|------|--------|-----|------|
| `default` | `allowed_tools` 외 → `can_use_tool` 콜백 호출. 콜백 없으면 차단(CLI는 사용자 프롬프트) | O | O | 기본값, 인터랙티브 앱 |
| `acceptEdits` | 파일 수정(Edit, Write, 파일시스템 명령)까지 자동 승인. 나머지는 `default`와 동일 | O | O | 코딩 에이전트 |
| `bypassPermissions` | 모든 도구 자동 승인 (`disallowed_tools` 제외) | O | O | 서버 자동화 |
| `plan` | 도구 실행 없음, 분석/계획만 출력 | O | O | dry-run, 사전 검토 |
| `dontAsk` | `allowed_tools` 외 → 즉시 거부 (콜백도 안 부름) | X | O | 엄격한 제한 (TS only) |

### 엄격도 스펙트럼

```
엄격                                                          느슨
 ←──────────────────────────────────────────────────────────→
plan        dontAsk        default       acceptEdits      bypass
(실행 안함)  (허용 외 거부)  (콜백 판단)   (+파일수정 허용)  (전부 허용)
```

### 권한 평가 순서 (전체)

도구 실행 요청이 왔을 때 SDK 내부에서 거치는 순서:

```
1. Hooks (PreToolUse)     → allow / deny / 다음으로
2. disallowed_tools       → 매칭되면 무조건 deny (bypass에서도)
3. permission_mode        → bypass면 여기서 allow
4. allowed_tools          → 매칭되면 allow
5. can_use_tool 콜백      → 코드에서 판단
6. (CLI only) 사용자 프롬프트 → 터미널에서 Y/N
```

### mode별 동작 예시

```python
# ── default: 콜백이 판단 ──
options = ClaudeAgentOptions(
    permission_mode="default",
    allowed_tools=["Read", "Grep"],     # 이것만 자동 승인
    can_use_tool=my_callback,           # 나머지는 콜백이 판단
)
# Read → 자동 승인
# Bash → can_use_tool 호출 → 콜백이 allow/deny 결정
# 콜백 없으면 → CLI: 사용자에게 물어봄 / 서버: 차단

# ── acceptEdits: 파일 수정까지 자동 ──
options = ClaudeAgentOptions(
    permission_mode="acceptEdits",
    allowed_tools=["Read", "Grep"],
    can_use_tool=my_callback,
)
# Read → 자동 승인 (allowed_tools)
# Write → 자동 승인 (acceptEdits가 파일 수정 허용)
# Bash → can_use_tool 호출

# ── bypassPermissions: 전부 통과 ──
options = ClaudeAgentOptions(
    permission_mode="bypassPermissions",
    disallowed_tools=["Bash"],          # 이것만 차단 (bypass에서도)
)
# Read → 자동 승인
# Write → 자동 승인
# Bash → 차단 (disallowed_tools)

# ── plan: 실행 없이 계획만 ──
options = ClaudeAgentOptions(
    permission_mode="plan",
)
# 모든 도구 → 실행 안 함, 에이전트가 "이렇게 하겠습니다"만 출력
# 계획 확인 후 다른 mode로 재실행하는 2단계 패턴에 활용

# ── dontAsk (TS only): 엄격한 화이트리스트 ──
# allowed_tools에 없으면 콜백도 안 부르고 즉시 거부
```

### 서버 환경에서의 선택 가이드

| 시나리오 | 추천 mode | 조합 |
|----------|----------|------|
| 완전 자동화 (신뢰할 수 있는 도구만) | `bypassPermissions` | + `disallowed_tools`로 위험 도구 차단 |
| 조건부 승인 필요 (파일 경로 검사 등) | `default` | + `allowed_tools` + `can_use_tool` 콜백 |
| 코딩 에이전트 (파일 수정 OK, 실행은 검토) | `acceptEdits` | + `can_use_tool`로 Bash 검토 |
| 사전 검토 후 실행 | `plan` → `bypassPermissions` | 2단계 실행 |

### 실전: pmai, daggle 모두 bypassPermissions

서버 환경에서 사용자 승인 UI가 없으므로 `bypassPermissions`가 사실상 유일한 실용적 선택.
도구 범위는 `allowed_tools`로, 절대 차단은 `disallowed_tools`로 제어.

```python
# 서버 자동화 표준 패턴
options = ClaudeAgentOptions(
    permission_mode="bypassPermissions",
    allowed_tools=[...],          # 화이트리스트로 범위 제한
    disallowed_tools=["Bash"],    # 위험한 도구는 블랙리스트로 차단
)
```

---

## 11. 사용자 입력 처리

공식 문서: https://platform.claude.com/docs/en/agent-sdk/user-input

### can_use_tool 콜백 — 동적 승인

`default` 또는 `acceptEdits` 모드에서 `allowed_tools`에 없는 도구가 호출될 때 실행되는 콜백.
서버 환경에서 `bypassPermissions` 대신 세밀한 제어가 필요할 때 사용.

```python
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny

async def can_use_tool(tool_name, input_data, context):
    if tool_name == "AskUserQuestion":
        # 질문 처리
        return await handle_questions(input_data)

    # 도구 승인/거부
    if tool_name == "Bash" and "rm" in input_data.get("command", ""):
        return PermissionResultDeny(message="삭제 명령 불허")

    return PermissionResultAllow(updated_input=input_data)

options = ClaudeAgentOptions(
    permission_mode="default",
    allowed_tools=["Read", "Grep", "Glob"],  # 이건 콜백 안 거치고 바로 승인
    can_use_tool=can_use_tool,               # 나머지는 여기서 판단
)
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

## 12. Hooks

공식 문서: https://platform.claude.com/docs/en/agent-sdk/hooks

에이전트 실행의 주요 시점에서 커스텀 코드 실행.

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

## 13. 서브에이전트

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

### 서브에이전트가 받는 것

- 자체 시스템 프롬프트 + Agent 도구의 prompt
- CLAUDE.md (settingSources로 로드 시)
- 도구 정의 (부모에서 상속 또는 tools 지정)

**받지 않는 것:** 부모의 대화 이력, 도구 결과, 시스템 프롬프트

### 서브에이전트 제약

- 자체 서브에이전트 생성 불가 (1단계 깊이만)
- Agent를 tools에 포함하지 말 것

### 실전: 두 프로젝트 모두 서브에이전트 미사용

- **pmai**: 용도별로 별도 `query()` 호출 (run_code_review, run_project_analysis 등)
- **daggle**: 단일 `query()` 호출, phase별 Skills로 행동 분리

서브에이전트 대신 **용도별 query()를 분리 호출**하는 게 현재 두 프로젝트의 패턴.

---

## 14. 세션 관리

공식 문서: https://platform.claude.com/docs/en/agent-sdk/sessions

### 자동 세션 관리 (ClaudeSDKClient)

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

### 세션 ID 캡처 및 재개

```python
session_id = None

async for message in query(prompt="분석해줘", options=options):
    if isinstance(message, SystemMessage):
        session_id = message.session_id
    elif isinstance(message, ResultMessage):
        session_id = message.session_id

# 나중에 세션 재개
async for message in query(
    prompt="아까 분석한 거 리팩토링해줘",
    options=ClaudeAgentOptions(resume=session_id),
):
    ...
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

---

## 15. 메시지 타입

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
│ thinking           │ Claude의 내부 사고 과정                         │
│ text               │ 사용자에게 보여주는 설명/응답                    │
│ tool_use           │ 도구 호출 — name, input 포함                    │
└────────────────────┴────────────────────────────────────────────────┘
```

### 메시지 처리 예시

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

async for message in query(prompt="버그 고쳐줘", options=options):
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if block.type == "thinking":
                print("thinking:", block.thinking)
            elif block.type == "text":
                print("text:", block.text)
            elif block.type == "tool_use":
                print("tool:", block.name, block.input)
    elif isinstance(message, ResultMessage):
        print("done:", message.result)
```

---

## 16. 스트리밍 출력

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

---

## 17. 토큰 사용량 및 과금

### 토큰 종류별 과금 (Anthropic API)

| 토큰 종류 | 설명 | 과금 배율 | Opus 단가 |
|:-----------|:-----|:---------|:----------|
| `input_tokens` | 캐시에 해당하지 않는 새 입력 토큰 | 1x | $15 / MTok |
| `cache_creation_input_tokens` | 캐시에 새로 쓴 토큰 (ephemeral_5m) | 1.25x | $18.75 / MTok |
| `cache_read_input_tokens` | 기존 캐시에서 읽은 토큰 | 0.1x | $1.50 / MTok |
| `output_tokens` | 모델이 생성한 출력 토큰 | 1x | $75 / MTok |

세 가지 input 토큰의 합 = 해당 API 호출의 전체 컨텍스트 크기. 매 호출마다 시스템 프롬프트 + 대화 히스토리 + 도구 정의가 캐시 토큰으로 재전송되므로, 호출 간 누적 합산하면 의미 없이 뻥튀기됨.

### SDK 메시지별 usage 데이터

| 메시지 타입 | usage 위치 | 정확성 | 비고 |
|:-----------|:-----------|:------|:-----|
| `StreamEvent (message_start)` | `event.message.usage` | input 정확, output 부정확 | output_tokens는 스트리밍 시작 시점 스냅샷 (부분값) |
| `StreamEvent (message_delta)` | `event.usage` | output 정확 | output_tokens가 해당 호출의 최종값. input 없음 |
| `AssistantMessage` | `message.usage` | input 정확, output 부정확 | message_start와 동일한 스냅샷. **사용 비권장** |
| `ResultMessage` | `message.usage` | 전체 합산 정확 | 전 턴의 input/output/cache 합산 + `total_cost_usd` 포함 |

### ResultMessage 필드

```python
# ResultMessage 주요 필드
message.usage          # dict: input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens
message.total_cost_usd # float: 전체 세션의 실제 과금액 (캐시 할인 반영)
message.model_usage    # dict: 모델별 사용량 상세
message.duration_ms    # int: 전체 소요 시간
message.num_turns      # int: 대화 턴 수
```

### 실시간 토큰 트래킹 권장 방식

```python
# message_delta에서 output_tokens 실시간 추적 (per-API-call 최종값)
if ev_type == "message_delta":
    usage = ev.get("usage", {})
    output_tokens = usage.get("output_tokens", 0)  # 이 호출의 최종 output

# ResultMessage에서 세션 전체 비용 확인
if isinstance(message, ResultMessage):
    total_cost = message.total_cost_usd  # 실제 과금액
    usage = message.usage                # 전체 합산 토큰
```

**주의사항:**
- `AssistantMessage.usage.output_tokens`는 스트리밍 시작 시점 값이므로 실제보다 훨씬 적게 나옴. 사용 금지.
- `cache_creation_input_tokens + cache_read_input_tokens`를 호출 간 누적하면 컨텍스트가 중복 카운팅됨.
- 사용자에게 보여줄 값으로는 `output_tokens` 누적 (실시간) 또는 `total_cost_usd` (완료 시)를 권장.

---

## 18. 구조화된 출력

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
``` """

# 후처리에서 파싱
if "json:issues" in result_text:
    issues_json = extract_json_block(result_text, "issues")
```

---

## 19. 리소스 제한 — 비용/턴/버퍼

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

## 20. 입력 모드

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

## 21. 슬래시 명령어

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

## 22. 플러그인

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

## 23. Playwright MCP 트러블슈팅

pmai에서 Playwright MCP를 동작시키기까지 겪은 문제들 정리.

### 1. MCP 도구를 아예 못 찾음

**증상**: `ToolSearch`에서 `mcp__playwright__*` 도구가 안 나옴. GitHub/PM Agent MCP는 정상.

**원인**: CLI 인자가 잘못되어 MCP 서버가 시작 즉시 종료됨. MCP 서버 시작 실패는 조용히 무시됨.

| 문제 | 기존값 | 수정 |
|------|--------|------|
| `--browser` | `chromium` (미지원) | `chrome` |
| `--viewport-size` | `1280,720` (콤마) | `1280x720` (x) |
| `--cap-screenshot-height` | 존재하지 않는 옵션 | 제거 |

**교훈**: `npx @playwright/mcp --help`로 인자 확인 필수. `debug_stderr: True` 항상 설정.

### 2. 도구 등록 버그 (@playwright/mcp 버전)

**증상**: MCP 서버는 시작되지만 도구 목록이 Claude에 노출 안 됨.

**원인**: `@playwright/mcp` 최신 버전(0.0.56+)에서 도구 등록 버그. (Issue [microsoft/playwright-mcp#1359](https://github.com/microsoft/playwright-mcp/issues/1359))

**해결**: `@playwright/mcp@0.0.41`로 버전 고정. Dockerfile에서 `npm install -g @playwright/mcp@0.0.41`.

### 3. Chrome 경로 불일치

**증상**: `Chromium distribution 'chrome' is not found at /opt/google/chrome/chrome`

**원인**: Dockerfile에서 `npx playwright install chromium`으로 Chromium 설치했는데, MCP는 Chrome(`/opt/google/chrome/chrome`)을 찾음.

**해결**: `npx playwright install --with-deps chrome`으로 Chrome 설치.

### 4. 스크린샷 1MB 버퍼 초과

**증상**: `Failed to decode JSON: JSON message exceeded maximum buffer size of 1048576 bytes`

**원인**: Playwright 스크린샷이 base64로 인코딩되어 JSON에 포함 → SDK의 1MB 버퍼 제한 초과.

**해결**: `ClaudeAgentOptions(max_buffer_size=10*1024*1024)`. 스크린샷을 유지하면서 버퍼만 늘림.

### 최종 동작하는 설정

```python
# executor.py
extra_mcp = {
    "playwright": {
        "command": "npx",
        "args": ["@playwright/mcp", "--headless", "--viewport-size", "1280x720"],
    },
}

options = ClaudeAgentOptions(
    mcp_servers=extra_mcp,
    allowed_tools=["mcp__playwright__*"],
    max_buffer_size=10 * 1024 * 1024,  # 10MB
    include_partial_messages=True,
    debug_stderr=True,
    permission_mode="bypassPermissions",
)
```

```dockerfile
# Dockerfile
RUN npm install -g @anthropic-ai/claude-code @playwright/mcp@0.0.41
RUN npx playwright install --with-deps chrome
```

---

## 24. 알려진 제한사항

- **Extended thinking**: `max_thinking_tokens` 설정 시 StreamEvent가 발생하지 않음
- **Structured output**: JSON 결과는 최종 ResultMessage.structured_output에서만 제공
- **SDK MCP + include_partial_messages 충돌**: `create_sdk_mcp_server`(인프로세스 MCP)와 `include_partial_messages=True`를 함께 사용하면 백프레셔 데드락 발생. StreamEvent 대량 발생 → 내부 메시지 큐(버퍼 100) 포화 → MCP 제어 메시지 처리 불가 → 도구 실패/행. stdio MCP(command+args 외부 프로세스)는 별도 파이프라서 영향 없음. (Issue [#425](https://github.com/anthropics/claude-agent-sdk-python/issues/425), [#701](https://github.com/anthropics/claude-agent-sdk-python/issues/701) — 미해결)
- **SDK MCP stdin 타임아웃**: SDK MCP 사용 시 60초 후 stdin이 닫혀 MCP 통신 끊김. SDK >= 0.1.50에서 수정됨 (PR #731). 구버전 임시 해결: `CLAUDE_CODE_STREAM_CLOSE_TIMEOUT=3600000`. (Issue [#730](https://github.com/anthropics/claude-agent-sdk-python/issues/730))
- **스트리밍 루프에서 break 금지**: `async for message in query(...)` 루프에서 ResultMessage 수신 후 `break`하면 generator 강제 중단으로 `RuntimeError: cancel scope` 에러 발생. break 없이 generator가 자연 종료되도록 해야 함. (pmai 트러블슈팅에서 발견)
- **JSON 버퍼 1MB 제한**: MCP 응답(특히 Playwright 스크린샷 base64)이 1MB를 초과하면 `CLIJSONDecodeError` 발생. `max_buffer_size=10*1024*1024`로 해결. (Issue [#98](https://github.com/anthropics/claude-agent-sdk-python/issues/98))

---

## 25. 실전 패턴 비교 — pmai vs daggle

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

## 26. 에이전트 구성 의사결정 플로우차트

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

---

## 27. 마이그레이션 가이드

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

## 28. GitHub 저장소

- Python SDK: https://github.com/anthropics/claude-agent-sdk-python
- TypeScript SDK: https://github.com/anthropics/claude-agent-sdk-typescript
- 예제 에이전트: https://github.com/anthropics/claude-agent-sdk-demos

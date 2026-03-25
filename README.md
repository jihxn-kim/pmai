# PM Agent

AI 기반 프로젝트 관리 플랫폼. GitHub, Slack, Google Calendar, Notion과 연동하여 여러 프로젝트를 관리하고, AI가 코드리뷰, 진척도 분석, 주간 브리핑을 자동으로 수행합니다.

## 기능

- **프로젝트 관리**: 조직/프로젝트/태스크 관리, 칸반 보드, 팀원 배정
- **GitHub 연동**: PR/이슈 실시간 sync, webhook 기반 자동 처리
- **AI 엔진**: 코드리뷰, 프로젝트 분석, 테스트 시나리오 생성, 주간 브리핑 (Claude Agent SDK)
- **Slack 봇**: 자연어 대화로 프로젝트 상태 확인, 자동 알림, 마감 리마인더
- **Google Calendar**: 태스크 마감일 양방향 sync, 회의 전 자동 브리핑
- **Notion**: 태스크 양방향 sync, 문서 활용, 브리핑 페이지 자동 생성

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| Database | PostgreSQL 16 |
| AI | Claude Agent SDK |
| 인프라 | Docker Compose |

---

## 빠른 시작

### 사전 요구사항

- Docker + Docker Compose
- Python 3.12+
- Node.js 20+
- Git

### 1. 저장소 클론

```bash
git clone git@github.com:jihxn-kim/pmai.git
cd pmai
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
cp .env backend/.env
```

> **중요:** `.env` 파일은 프로젝트 루트와 `backend/` 디렉토리 **양쪽에** 있어야 합니다. 루트의 `.env`는 Docker Compose용, `backend/.env`는 로컬 개발 시 FastAPI가 읽습니다.

`.env` 파일을 열고 필수 값들을 채웁니다:

```env
# 필수: JWT 시크릿 (아래 명령어로 생성)
# openssl rand -hex 32
JWT_SECRET_KEY=생성된_랜덤_문자열

# 필수: GitHub App (아래 "GitHub App 설정" 참고)
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
GITHUB_APP_ID=your_app_id
NEXT_PUBLIC_GITHUB_CLIENT_ID=GITHUB_CLIENT_ID와_동일한_값

# 프론트엔드 URL (포트가 3000이 아닌 경우 변경)
FRONTEND_URL=http://localhost:3000
```

> **포트 충돌 시:** 프론트엔드가 3000이 아닌 다른 포트(예: 3003)로 뜨면, `FRONTEND_URL`을 해당 포트로 변경하세요. `.env`를 수정한 후에는 반드시 `backend/.env`에도 복사하고 백엔드를 재시작해야 합니다.

### 3. 데이터베이스 실행

```bash
docker compose up db -d
```

### 4. 백엔드 실행

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 5. 프론트엔드 실행 (새 터미널)

```bash
cd frontend
npm install
npm run dev
```

### 6. 접속

- 대시보드: http://localhost:3000
- API 문서 (Swagger): http://localhost:8000/docs
- 헬스체크: http://localhost:8000/api/health

---

## 외부 서비스 설정

### GitHub App (필수 - 로그인에 필요)

1. https://github.com/settings/apps/new 접속
2. 다음 값들을 입력:

| 항목 | 값 |
|------|---|
| App name | PM Agent (아무 이름) |
| Homepage URL | `http://localhost:3000` |
| Callback URL | `http://localhost:8000/api/auth/github/callback` |
| Setup URL | `http://localhost:8000/api/github/setup/callback` |
| Webhook active | 체크 해제 (로컬 개발 시) |

3. Permissions 설정:
   - **Contents**: Read-only
   - **Issues**: Read & write
   - **Pull requests**: Read & write
   - **Metadata**: Read-only (기본값)

4. "Where can this GitHub App be installed?" → **Only on this account**

5. **Private Key 생성**:
   - 앱 설정 페이지 하단 "Private keys" → "Generate a private key" 클릭
   - `.pem` 파일 다운로드됨

6. 생성 후 받은 값들을 `.env`에 입력:

```env
GITHUB_CLIENT_ID=앱의_Client_ID
GITHUB_CLIENT_SECRET=Generate_a_new_client_secret_버튼으로_생성
GITHUB_APP_ID=앱_설정_페이지_상단의_App_ID
GITHUB_APP_SLUG=앱_URL_슬러그 (github.com/settings/apps/여기 부분)
NEXT_PUBLIC_GITHUB_CLIENT_ID=GITHUB_CLIENT_ID와_동일한_값
```

Private Key는 여러 줄이라 `.env`에 넣을 때 **따옴표로 감싸고 `\n`으로 변환**해야 합니다:

```bash
# .pem 파일을 .env용 한 줄 문자열로 변환
awk '{printf "%s\\n", $0}' your-app.private-key.pem
```

출력된 값을 `.env`에 따옴표로 감싸서 입력:
```env
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n"
```

7. **GitHub App 설치** (레포 접근 권한 부여):
   - 대시보드 Settings 페이지에서 "GitHub App 설치" 버튼 클릭
   - 또는 직접: `https://github.com/apps/{GITHUB_APP_SLUG}/installations/new`
   - 계정 선택 → 레포 선택 → Install
   - 자동으로 대시보드로 돌아오면서 installation_id가 저장됨

7. (선택) GitHub webhook을 로컬에서 받으려면 ngrok 필요:

```bash
ngrok http 8000
# 나온 URL을 GitHub App의 Webhook URL에 입력
# Webhook active 체크, Webhook Secret 생성 후 .env에 입력
```

### Slack App (선택 - Slack 봇 기능)

1. https://api.slack.com/apps → "Create New App" → "From scratch"
2. App name: PM Agent, Workspace: 본인 워크스페이스

3. 좌측 메뉴에서 설정:
   - **OAuth & Permissions** → Bot Token Scopes 추가:
     - `chat:write`, `app_mentions:read`, `users:read`, `channels:read`
   - **Event Subscriptions** → Enable Events ON:
     - Request URL: `https://your-ngrok-url/api/slack/events`
     - Subscribe to bot events: `app_mention`

4. 좌측 "Basic Information"에서 값 확인 → `.env`에 입력:

```env
SLACK_CLIENT_ID=Basic_Information의_Client_ID
SLACK_CLIENT_SECRET=Client_Secret
SLACK_SIGNING_SECRET=Signing_Secret
```

5. 대시보드 설정 페이지에서 "Slack 연결" 클릭하면 OAuth로 자동 연결

### Google Calendar (선택 - 캘린더 연동)

1. https://console.cloud.google.com/ → 프로젝트 생성
2. "APIs & Services" → "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
3. Application type: Web application
4. Authorized redirect URIs: `http://localhost:8000/api/calendar/oauth/callback`
5. "Google Calendar API" 활성화 (APIs & Services → Library)

```env
GOOGLE_CLIENT_ID=생성된_Client_ID
GOOGLE_CLIENT_SECRET=Client_Secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/calendar/oauth/callback
```

6. 대시보드 설정 페이지에서 "Google Calendar 연결" 클릭

### Notion (선택 - Notion 연동)

1. https://www.notion.so/my-integrations → "New integration"
2. Type: Public integration
3. Redirect URIs: `http://localhost:8000/api/notion/oauth/callback`
4. Capabilities: Read content, Update content, Insert content

```env
NOTION_CLIENT_ID=OAuth_client_ID
NOTION_CLIENT_SECRET=OAuth_client_secret
NOTION_REDIRECT_URI=http://localhost:8000/api/notion/oauth/callback
```

5. 대시보드 설정 페이지에서 "Notion 연결" 클릭

---

## Docker Compose로 전체 실행

모든 `.env` 값을 채운 후:

```bash
docker compose up --build
```

- PostgreSQL: `localhost:5432`
- Backend: `localhost:8000`
- Frontend: `localhost:3000`

---

## 테스트

```bash
cd backend
source .venv/bin/activate
python -m pytest -v
```

현재 59개 테스트 전부 통과.

---

## 프로젝트 구조

```
pmai/
├── backend/                    # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py             # 앱 엔트리포인트
│   │   ├── config.py           # 환경 설정
│   │   ├── database.py         # DB 연결
│   │   ├── dependencies.py     # 인증/권한 의존성
│   │   ├── scheduler.py        # APScheduler (브리핑, 리마인더, 폴링)
│   │   ├── models/             # SQLAlchemy 모델 (15개 테이블)
│   │   ├── schemas/            # Pydantic 스키마
│   │   ├── routers/            # API 라우터 (10개)
│   │   └── services/           # 비즈니스 로직
│   │       ├── ai/             # AI Agent Engine (Phase 2)
│   │       ├── slack/          # Slack 봇 (Phase 3)
│   │       ├── calendar/       # Google Calendar (Phase 4)
│   │       └── notion/         # Notion (Phase 4)
│   ├── alembic/                # DB 마이그레이션
│   └── tests/                  # 59개 테스트
├── frontend/                   # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/                # 페이지 (9개 라우트)
│   │   ├── components/         # UI 컴포넌트
│   │   ├── hooks/              # React Query 훅
│   │   └── lib/                # API 클라이언트, 유틸
├── docs/                       # 설계 문서
│   └── superpowers/
│       ├── specs/              # Phase 1~4 설계 스펙
│       └── plans/              # Phase 1~4 구현 계획
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## API 엔드포인트 요약

| 영역 | 주요 엔드포인트 |
|------|---------------|
| 인증 | `GET /api/auth/github`, `GET /api/auth/me`, `POST /api/auth/refresh` |
| 조직 | `GET/POST /api/orgs`, `GET/PATCH /api/orgs/{id}` |
| 프로젝트 | `POST /api/orgs/{id}/projects`, `GET/PATCH/DELETE /api/projects/{id}` |
| 태스크 | `POST /api/projects/{id}/tasks`, `GET/PATCH/DELETE /api/tasks/{id}` |
| GitHub | `POST /api/webhooks/github`, `GET /api/projects/{id}/pulls` |
| 대시보드 | `GET /api/orgs/{id}/dashboard`, `GET /api/me/tasks` |
| AI | `POST /api/projects/{id}/ai/analyze`, `POST .../ai/review/{pr}` |
| 브리핑 | `GET /api/orgs/{id}/briefings`, `POST .../briefings/generate` |
| Slack | `POST /api/slack/events`, `GET /api/orgs/{id}/slack/status` |
| Calendar | `GET /api/calendar/auth`, `GET /api/users/me/calendar/status` |
| Notion | `GET /api/orgs/{id}/notion/auth`, `POST /api/projects/{id}/notion/database` |

전체 API 목록은 `http://localhost:8000/docs`에서 확인.

---

## 프로덕션 배포 시 변경사항

배포할 때 GitHub App 자체를 다시 만들 필요는 없습니다. URL만 변경하면 됩니다:

### GitHub App 설정 변경 (https://github.com/settings/apps/your-app)

| 항목 | 로컬 | 프로덕션 |
|------|------|---------|
| Homepage URL | `http://localhost:3000` | `https://your-domain.com` |
| Callback URL | `http://localhost:8000/api/auth/github/callback` | `https://api.your-domain.com/api/auth/github/callback` |
| Setup URL | `http://localhost:8000/api/github/setup/callback` | `https://api.your-domain.com/api/github/setup/callback` |
| Webhook URL | (비활성) | `https://api.your-domain.com/api/webhooks/github` |
| Webhook active | 체크 해제 | **체크** (프로덕션에서는 활성화) |

### `.env` 변경

```env
DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/pmai
FRONTEND_URL=https://your-domain.com
GOOGLE_REDIRECT_URI=https://api.your-domain.com/api/calendar/oauth/callback
NOTION_REDIRECT_URI=https://api.your-domain.com/api/notion/oauth/callback
```

### 기타 프로덕션 설정
- JWT 쿠키의 `secure=True` 활성화 (HTTPS 필수)
- `GITHUB_WEBHOOK_SECRET` 설정 (webhook 서명 검증)
- Slack App의 Event URL과 Redirect URL도 프로덕션 도메인으로 변경
- Google OAuth의 Authorized redirect URIs도 변경
- Notion Integration의 Redirect URIs도 변경

---

## Claude Agent SDK 참조 문서

PM Agent의 AI 기능은 Claude Agent SDK를 사용합니다. 개발/커스터마이징 시 아래 공식 문서를 참고하세요.

**공식 문서**: https://platform.claude.com/docs/en/agent-sdk

| 페이지 | 설명 | URL |
|--------|------|-----|
| Overview | SDK 소개, 설치, 기본 사용법 | `/docs/en/agent-sdk/overview` |
| Quickstart | 버그 수정 agent 만들기 튜토리얼 | `/docs/en/agent-sdk/quickstart` |
| Streaming Output | 실시간 텍스트/도구 스트리밍 (`StreamEvent`, `include_partial_messages`) | `/docs/en/agent-sdk/streaming-output` |
| Streaming vs Single Mode | 입력 모드 선택 (interactive vs one-shot) | `/docs/en/agent-sdk/streaming-vs-single-mode` |
| Permissions | 도구 권한 제어 (`allowed_tools`, `permission_mode`) | `/docs/en/agent-sdk/permissions` |
| Handle User Input | 사용자 승인/질문 처리 (`AskUserQuestion`) | `/docs/en/agent-sdk/user-input` |
| Hooks | agent 라이프사이클 콜백 (`PreToolUse`, `PostToolUse`, `Stop` 등) | `/docs/en/agent-sdk/hooks` |
| Subagents | 서브에이전트 정의 및 실행 | `/docs/en/agent-sdk/subagents` |
| Sessions | 세션 유지/복원 (`resume`, `fork`) | `/docs/en/agent-sdk/sessions` |
| MCP | Model Context Protocol 서버 연결 | `/docs/en/agent-sdk/mcp` |
| Custom Tools | 커스텀 도구 생성 (`@tool`, `create_sdk_mcp_server`) | `/docs/en/agent-sdk/custom-tools` |
| Structured Output | JSON 스키마 응답 (`output_format`) | `/docs/en/agent-sdk/structured-outputs` |
| System Prompts | 시스템 프롬프트 수정, CLAUDE.md 활용 | `/docs/en/agent-sdk/modifying-system-prompts` |
| Skills | 스킬 파일 정의 (`.claude/skills/`) | `/docs/en/agent-sdk/skills` |
| Slash Commands | 커스텀 명령어 (`.claude/commands/`) | `/docs/en/agent-sdk/slash-commands` |
| Plugins | 플러그인 확장 | `/docs/en/agent-sdk/plugins` |
| Migration Guide | 이전 SDK에서 마이그레이션 | `/docs/en/agent-sdk/migration-guide` |

### 주요 메시지 타입

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

### 실시간 스트리밍 (StreamEvent)

`include_partial_messages=True` 설정 시 토큰 단위 스트리밍:

```python
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import StreamEvent

async for message in query(prompt="...", options=ClaudeAgentOptions(
    include_partial_messages=True,
    allowed_tools=["Read", "Bash"],
)):
    if isinstance(message, StreamEvent):
        event = message.event
        if event.get("type") == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                print(delta.get("text", ""), end="")  # 실시간 텍스트
            elif delta.get("type") == "input_json_delta":
                print(delta.get("partial_json", ""), end="")  # 도구 입력
```

### GitHub 저장소

- Python SDK: https://github.com/anthropics/claude-agent-sdk-python
- TypeScript SDK: https://github.com/anthropics/claude-agent-sdk-typescript
- 예제 에이전트: https://github.com/anthropics/claude-agent-sdk-demos

---

## 개발 Phase

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | 코어 플랫폼 + GitHub 연동 + 웹 대시보드 | 완료 |
| 2 | AI Agent 엔진 (코드리뷰, 분석, 브리핑) | 완료 |
| 3 | Slack 봇 + 자동화 (알림, 리마인더) | 완료 |
| 4 | Google Calendar + Notion 연동 | 완료 |

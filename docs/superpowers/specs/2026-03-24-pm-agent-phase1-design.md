# PM Agent - Phase 1 Design: Core Platform + GitHub + Dashboard

## Overview

소규모 팀이 여러 프로젝트를 관리할 수 있는 PM Agent 플랫폼의 Phase 1.
프로젝트별 팀원 배정, GitHub 연동을 통한 실시간 진척도 추적, 웹 대시보드를 제공한다.

### Full Project Phases

| Phase | 범위 | 의존성 |
|-------|------|--------|
| **1 (이번)** | 코어 플랫폼 + GitHub 연동 + 웹 대시보드 | - |
| 2 | AI Agent 엔진 (코드리뷰, 진척도 분석, 태스크 계획) | Phase 1 |
| 3 | Slack 봇 + 자동화 엔진 (알림, 이벤트 트리거) | Phase 1 |
| 4 | Google Calendar + Notion 연동 | Phase 1 |

### Phase 1 Scope

**포함:**
- 조직/프로젝트/팀원 관리 CRUD
- GitHub 레포 연결 + webhook으로 PR/이슈 실시간 sync
- 웹 대시보드 (조직 현황, 프로젝트 상세, 칸반 보드, 개인 뷰)
- 진척도 자동 계산 + 문제점 표시 (지연 태스크, 오래된 PR)

**제외 (이후 Phase):**
- AI 코드리뷰, 테스트 시나리오, 자율 판단 (Phase 2)
- Slack 봇, 자동 알림, 이벤트 트리거 (Phase 3)
- Google Calendar, Notion 연동 (Phase 4)

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              Next.js (Frontend)              │
│         웹 대시보드 / 프로젝트 현황           │
└──────────────────┬──────────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────────┐
│             FastAPI (Backend)                │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ Auth     │ │ Project  │ │ GitHub      │  │
│  │ Service  │ │ Service  │ │ Integration │  │
│  └──────────┘ └──────────┘ └─────────────┘  │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────▼─────────┐
         │   PostgreSQL      │
         └───────────────────┘
```

### Tech Stack

| 레이어 | 기술 | 이유 |
|--------|------|------|
| Backend | FastAPI (Python) | 비동기 처리, AI 생태계 확장성 |
| Frontend | Next.js (App Router) | SSR, 대시보드 최적 |
| DB | PostgreSQL | 관계형 데이터, 팀/프로젝트/태스크 |
| ORM | SQLAlchemy + Alembic | 마이그레이션 관리 |
| UI | Tailwind CSS + shadcn/ui | 빠른 UI 개발 |
| Data Fetching | React Query (TanStack Query) | 서버 상태 관리, 캐싱 |

---

## Data Model

### User

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| github_id | INTEGER | GitHub 사용자 ID |
| github_username | VARCHAR | GitHub 로그인명 |
| name | VARCHAR | 표시 이름 |
| email | VARCHAR | 이메일 |
| avatar_url | VARCHAR | GitHub 프로필 이미지 |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

### Organization

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| name | VARCHAR | 조직 이름 |
| slug | VARCHAR | URL용 슬러그 (unique) |
| owner_id | UUID | FK → User |
| github_installation_id | INTEGER | GitHub App 설치 ID (nullable) |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

### OrgMember

| 필드 | 타입 | 설명 |
|------|------|------|
| org_id | UUID | PK (composite), FK → Organization |
| user_id | UUID | PK (composite), FK → User |
| role | ENUM | owner / admin / member |
| created_at | TIMESTAMP | 가입일 |
| updated_at | TIMESTAMP | 역할 변경일 |

### Project

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| org_id | UUID | FK → Organization |
| name | VARCHAR | 프로젝트 이름 |
| description | TEXT | 설명 |
| status | ENUM | active / paused / done |
| github_repo_url | VARCHAR | GitHub 레포 URL |
| github_repo_id | INTEGER | GitHub 레포 ID (unique — 하나의 레포는 하나의 프로젝트에만 연결) |
| start_date | DATE | 시작일 |
| end_date | DATE | 종료 예정일 |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

### ProjectMember

| 필드 | 타입 | 설명 |
|------|------|------|
| project_id | UUID | PK (composite), FK → Project |
| user_id | UUID | PK (composite), FK → User |
| role | ENUM | lead / developer / reviewer |
| created_at | TIMESTAMP | 배정일 |
| updated_at | TIMESTAMP | 역할 변경일 |

### Task

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| title | VARCHAR | 태스크 제목 |
| description | TEXT | 상세 설명 |
| assignee_id | UUID | FK → User (nullable) |
| status | ENUM | todo / in_progress / review / done |
| priority | ENUM | low / medium / high / critical |
| due_date | DATE | 마감일 (nullable) |
| github_issue_id | INTEGER | 연결된 GitHub 이슈 ID (nullable) |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

### PullRequest

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| github_pr_id | INTEGER | GitHub PR ID |
| number | INTEGER | PR 번호 |
| title | VARCHAR | PR 제목 |
| state | ENUM | open / merged / closed |
| author_id | UUID | FK → User (nullable) |
| review_state | ENUM | pending / approved / changes_requested (nullable) |
| merged_at | TIMESTAMP | 머지 시각 (nullable) |
| created_at | TIMESTAMP | 생성일 |
| updated_at | TIMESTAMP | 수정일 |

### PullRequestReviewer

| 필드 | 타입 | 설명 |
|------|------|------|
| pr_id | UUID | PK (composite), FK → PullRequest |
| user_id | UUID | PK (composite), FK → User |
| state | ENUM | pending / approved / changes_requested |
| submitted_at | TIMESTAMP | 리뷰 제출 시각 (nullable) |

### ActivityLog

| 필드 | 타입 | 설명 |
|------|------|------|
| id | UUID | PK |
| project_id | UUID | FK → Project |
| user_id | UUID | FK → User (nullable) |
| action | VARCHAR | 수행된 동작 (pr_opened, issue_created, task_moved 등) |
| detail | JSONB | 상세 데이터 |
| created_at | TIMESTAMP | 발생 시각 |

---

## Authentication & Authorization

### Authentication Flow

```
1. 사용자 → "GitHub으로 로그인" 클릭
2. GET /api/auth/github → state 파라미터 생성 + GitHub OAuth URL로 리다이렉트
3. GitHub 인증 완료 → /api/auth/github/callback으로 콜백
4. FastAPI에서 GitHub 사용자 정보 조회
5. DB에 User upsert (최초 시 생성, 이후 업데이트)
6. JWT 발급 (access token: 1h, refresh token: 7d)
   - refresh token은 httpOnly 쿠키에 저장 (XSS 방지)
   - access token은 응답 body로 전달, 메모리에 보관
   - refresh token은 DB에도 저장 (revocation 지원)
7. Next.js 클라이언트에서 Authorization 헤더로 API 호출
```

### Token Revocation

- 멤버 제거 시 해당 사용자의 refresh token을 DB에서 삭제 → 기존 access token 만료(1h) 후 접근 불가
- 로그아웃 시 refresh token 삭제 + httpOnly 쿠키 클리어

### Authorization (2-tier)

**Organization Level:**

| Role | Permissions |
|------|------------|
| Owner | 조직 설정 변경, 멤버 초대/제거, 프로젝트 생성/삭제, 모든 프로젝트 접근 |
| Admin | 프로젝트 생성, 멤버 초대, 모든 프로젝트 접근 |
| Member | 배정된 프로젝트만 접근 |

**Project Level:**

| Role | Permissions |
|------|------------|
| Lead | 프로젝트 설정 변경, 태스크 생성/배정/삭제, 멤버 관리 |
| Developer | 태스크 상태 변경, 본인 할당 태스크 관리 |
| Reviewer | 읽기 전용 + 리뷰 관련 작업 |

---

## GitHub Integration

### GitHub App

개인 토큰이 아닌 GitHub App으로 구현한다. 팀 사용에 적합하고, 조직 관리자가 한 번 설치하면 팀원 개별 토큰이 필요 없다.

**필요 권한:**
- Repository: read (코드, 이슈, PR)
- Pull requests: read (PR review 이벤트 수신 포함)
- Issues: read (Phase 1에서는 읽기만, Phase 2에서 write 권한 추가 요청)
- Webhooks: 자동 등록

### Webhook Security

- 모든 webhook 요청은 `X-Hub-Signature-256` 헤더로 서명 검증
- webhook secret은 GitHub App 설정 시 생성, 환경 변수로 관리

### Webhook Events

| Event | 처리 |
|-------|------|
| `pull_request` (opened/closed/merged) | PullRequest 테이블 upsert + ActivityLog 기록 |
| `issues` (opened/closed/edited) | Task와 연결 또는 신규 Task 생성 + ActivityLog |
| `push` | ActivityLog에 커밋 기록 |
| `pull_request_review` (submitted) | PullRequestReviewer upsert + PR review_state 업데이트 |

### GitHub Repo Connection Flow

```
1. 프로젝트 설정에서 "GitHub 연결" 클릭
2. GitHub App 설치 페이지로 리다이렉트 (미설치 시)
3. 레포 선택 → webhook 자동 등록
4. 기존 이슈/PR 초기 sync (asyncio.create_task로 백그라운드 실행)
5. 이후 webhook으로 실시간 유지
```

---

## API Endpoints

### Auth

```
GET    /api/auth/github               # GitHub OAuth 시작 (GitHub로 리다이렉트)
GET    /api/auth/github/callback      # GitHub OAuth 콜백 → JWT 발급 (GitHub이 GET으로 리다이렉트)
POST   /api/auth/refresh              # access token 갱신
POST   /api/auth/logout               # 로그아웃 (refresh token 삭제)
GET    /api/auth/me                   # 현재 사용자 정보
```

### Organizations

```
GET    /api/orgs                              # 내 조직 목록
POST   /api/orgs                              # 조직 생성
GET    /api/orgs/{org_id}                     # 조직 정보
PATCH  /api/orgs/{org_id}                     # 조직 수정
GET    /api/orgs/{org_id}/members             # 멤버 목록
POST   /api/orgs/{org_id}/members             # 멤버 추가 (github_username으로 직접 추가, 해당 유저가 플랫폼에 가입되어 있어야 함)
DELETE /api/orgs/{org_id}/members/{user_id}   # 멤버 제거
PATCH  /api/orgs/{org_id}/members/{user_id}   # 멤버 역할 변경
```

### Projects

```
POST   /api/orgs/{org_id}/projects                    # 프로젝트 생성
GET    /api/orgs/{org_id}/projects                    # 프로젝트 목록
GET    /api/projects/{project_id}                     # 프로젝트 상세 + 진척도
PATCH  /api/projects/{project_id}                     # 프로젝트 수정
DELETE /api/projects/{project_id}                     # 프로젝트 삭제
GET    /api/projects/{project_id}/members             # 프로젝트 멤버 목록
POST   /api/projects/{project_id}/members             # 멤버 배정
DELETE /api/projects/{project_id}/members/{user_id}   # 멤버 제거
PATCH  /api/projects/{project_id}/members/{user_id}   # 멤버 역할 변경
POST   /api/projects/{project_id}/github              # GitHub 레포 연결
```

### Tasks

```
POST   /api/projects/{project_id}/tasks       # 태스크 생성
GET    /api/projects/{project_id}/tasks       # 태스크 목록 (필터: status, assignee, priority)
GET    /api/tasks/{task_id}                   # 태스크 상세
PATCH  /api/tasks/{task_id}                   # 태스크 수정 (상태, 담당자, 마감일 등)
DELETE /api/tasks/{task_id}                   # 태스크 삭제
```

### GitHub Integration

```
POST   /api/webhooks/github                       # GitHub webhook 수신
GET    /api/projects/{project_id}/pulls            # PR 목록
GET    /api/projects/{project_id}/activity         # 활동 로그
```

### Dashboard

```
GET    /api/orgs/{org_id}/dashboard               # 조직 전체 현황 (프로젝트별 요약)
GET    /api/me/tasks                              # 내 태스크 (전체 프로젝트)
GET    /api/projects/{project_id}/progress        # 프로젝트 진척도 상세
GET    /api/projects/{project_id}/issues          # 문제점 (지연 태스크, 오래된 PR)
```

---

## Web Dashboard

### Pages

**1. 조직 대시보드** (`/org/{slug}`)
- 전체 프로젝트 카드 목록 (상태 뱃지, 진척도 바, 팀원 아바타)
- 팀원별 현재 할당 태스크 수
- 최근 활동 피드 (PR 머지, 이슈 생성, 태스크 완료 등)

**2. 프로젝트 상세** (`/org/{slug}/project/{project_id}`)
- 탭 구조:
  - **Overview**: 진척도 바, 기간, 상태 요약
  - **Tasks**: 칸반 보드 (todo → in_progress → review → done), 드래그 앤 드롭
  - **GitHub**: PR 목록, 오픈 이슈, 최근 커밋
  - **Team**: 프로젝트 멤버, 각자 담당 태스크
  - **Issues**: 지연된 태스크, 7일 이상 오픈된 PR, 리뷰 대기 항목

**3. 태스크 상세** (모달 또는 `/task/{task_id}`)
- 제목, 설명, 상태, 우선순위, 담당자, 마감일
- 연결된 GitHub 이슈/PR 링크
- 활동 로그

**4. 개인 뷰** (`/me`)
- 내 태스크 목록 (전체 프로젝트 통합)
- 리뷰 요청받은 PR
- 오늘/이번 주 마감 항목

**5. 설정** (`/org/{slug}/settings`)
- 조직 정보 수정
- 멤버 관리 (초대, 역할 변경, 제거)
- GitHub App 연결 관리

### UI Tech

- **Next.js 14+ App Router** — 페이지 라우팅, SSR
- **Tailwind CSS** — 스타일링
- **shadcn/ui** — 버튼, 모달, 드롭다운 등 기본 컴포넌트
- **TanStack Query** — 서버 데이터 페칭, 캐싱, 낙관적 업데이트
- **dnd-kit** — 칸반 보드 드래그 앤 드롭

---

## Project Structure

```
pmai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 앱 엔트리
│   │   ├── config.py                # 환경 설정
│   │   ├── database.py              # DB 연결, 세션
│   │   ├── models/                  # SQLAlchemy 모델
│   │   │   ├── user.py
│   │   │   ├── organization.py
│   │   │   ├── project.py
│   │   │   ├── task.py
│   │   │   ├── pull_request.py
│   │   │   └── activity_log.py
│   │   ├── schemas/                 # Pydantic 스키마
│   │   ├── routers/                 # API 라우터
│   │   │   ├── auth.py
│   │   │   ├── orgs.py
│   │   │   ├── projects.py
│   │   │   ├── tasks.py
│   │   │   ├── github.py
│   │   │   └── dashboard.py
│   │   ├── services/                # 비즈니스 로직
│   │   │   ├── auth_service.py
│   │   │   ├── project_service.py
│   │   │   ├── github_service.py
│   │   │   └── dashboard_service.py
│   │   └── middleware/              # 인증, CORS 등
│   ├── alembic/                     # DB 마이그레이션
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                     # Next.js App Router 페이지
│   │   ├── components/              # UI 컴포넌트
│   │   ├── lib/                     # API 클라이언트, 유틸
│   │   └── hooks/                   # 커스텀 훅
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml               # 로컬 개발 (backend + frontend + postgres)
└── docs/
```

---

## GitHub-to-User Mapping

Webhook 페이로드에 포함된 GitHub 사용자를 내부 User로 매핑하는 전략:

1. `github_id`로 User 테이블 조회
2. **매칭 성공**: 해당 User의 ID를 PullRequest.author_id 등에 설정
3. **매칭 실패** (플랫폼에 가입하지 않은 GitHub 사용자): nullable 필드는 null로 설정. ActivityLog의 detail JSONB에 GitHub username을 기록하여 추후 참조 가능

---

## Progress Calculation

프로젝트 진척도 계산 로직:

```
progress = count(status == 'done') / count(total tasks) * 100
```

- Task가 0개인 프로젝트는 진척도 0%
- 우선순위별 가중치 없음 (Phase 1은 단순 비율)
- 상태별 분포도 함께 반환: `{ todo: 3, in_progress: 5, review: 2, done: 10, total: 20, progress: 50 }`

---

## Issue Detection Thresholds

문제점 감지 기준 (Phase 1은 하드코딩, Phase 2에서 프로젝트별 설정 가능):

| 문제 유형 | 기준 |
|----------|------|
| 지연된 태스크 | `due_date < today AND status != 'done'` |
| 오래된 PR | `state == 'open' AND created_at < 7일 전` |
| 리뷰 대기 | `PullRequestReviewer.state == 'pending' AND submitted_at IS NULL AND PR.created_at < 3일 전` |
| 담당자 미배정 태스크 | `assignee_id IS NULL AND status != 'done'` |

---

## Pagination

목록 API는 공통 페이지네이션 지원:

```
GET /api/projects/{id}/tasks?page=1&per_page=20&sort=created_at&order=desc
```

- 기본값: `page=1`, `per_page=20`
- 응답에 `total`, `page`, `per_page`, `total_pages` 메타데이터 포함
- Activity log는 cursor 기반 페이지네이션 (시간순 스크롤)

---

## Error Handling

- API 에러는 일관된 JSON 형식: `{ "error": { "code": "NOT_FOUND", "message": "..." } }`
- HTTP 상태 코드 준수: 400 (잘못된 요청), 401 (미인증), 403 (권한 없음), 404 (없음)
- GitHub webhook 실패 시 재시도 큐 (Phase 1에서는 단순 로그, Phase 3에서 큐 도입)
- Rate limiting: Phase 1에서는 미적용. 프로덕션 배포 시 리버스 프록시(nginx/Caddy)에서 처리

---

## Testing Strategy

- **Backend**: pytest + httpx (API 테스트), 테스트용 PostgreSQL (Docker)
- **Frontend**: Vitest + React Testing Library (컴포넌트), Playwright (E2E)
- **CI**: GitHub Actions — lint, test, build 자동화

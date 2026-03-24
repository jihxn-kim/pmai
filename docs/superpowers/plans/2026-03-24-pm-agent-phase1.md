# PM Agent Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core PM Agent platform with team/project management, GitHub integration, and a web dashboard.

**Architecture:** FastAPI backend with PostgreSQL for data, Next.js frontend for the dashboard. GitHub App for repo integration via webhooks. JWT auth with GitHub OAuth.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16, Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-03-24-pm-agent-phase1-design.md`

---

## File Structure

### Backend (`backend/`)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, router registration, CORS
│   ├── config.py                  # Pydantic Settings (env vars)
│   ├── database.py                # async engine, sessionmaker, Base
│   ├── models/
│   │   ├── __init__.py            # re-export all models for Alembic
│   │   ├── user.py                # User, RefreshToken
│   │   ├── organization.py        # Organization, OrgMember
│   │   ├── project.py             # Project, ProjectMember
│   │   ├── task.py                # Task
│   │   ├── pull_request.py        # PullRequest, PullRequestReviewer
│   │   └── activity_log.py        # ActivityLog
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py              # PaginatedResponse, ErrorResponse
│   │   ├── auth.py                # TokenResponse, UserResponse
│   │   ├── organization.py        # OrgCreate, OrgResponse, MemberAdd...
│   │   ├── project.py             # ProjectCreate, ProjectResponse...
│   │   ├── task.py                # TaskCreate, TaskResponse, TaskUpdate
│   │   ├── pull_request.py        # PRResponse
│   │   ├── activity_log.py        # ActivityResponse
│   │   └── dashboard.py           # DashboardResponse, ProgressResponse, IssueResponse
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                # /api/auth/*
│   │   ├── orgs.py                # /api/orgs/*
│   │   ├── projects.py            # /api/projects/*, /api/orgs/{id}/projects
│   │   ├── tasks.py               # /api/tasks/*, /api/projects/{id}/tasks
│   │   ├── github.py              # /api/webhooks/github, /api/projects/{id}/pulls|activity
│   │   └── dashboard.py           # /api/orgs/{id}/dashboard, /api/me/tasks, progress, issues
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py        # GitHub OAuth, JWT, token management
│   │   ├── org_service.py         # Org + member CRUD
│   │   ├── project_service.py     # Project + member CRUD
│   │   ├── task_service.py        # Task CRUD
│   │   ├── github_service.py      # Webhook processing, initial sync, GitHub API calls
│   │   └── dashboard_service.py   # Progress calc, issue detection, dashboard aggregation
│   └── dependencies.py            # get_db, get_current_user, require_org_role, require_project_role
├── alembic/
│   ├── env.py
│   └── versions/                  # migration files
├── alembic.ini
├── tests/
│   ├── conftest.py                # test DB, test client, fixtures
│   ├── test_auth.py
│   ├── test_orgs.py
│   ├── test_projects.py
│   ├── test_tasks.py
│   ├── test_github.py
│   └── test_dashboard.py
├── requirements.txt
└── Dockerfile
```

### Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx                               # Root layout, providers
│   │   ├── page.tsx                                 # Landing / redirect to dashboard
│   │   ├── login/page.tsx                           # Login page
│   │   ├── auth/callback/page.tsx                   # OAuth callback handler
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx                           # Dashboard layout (sidebar, header)
│   │   │   ├── me/page.tsx                          # Personal view
│   │   │   └── org/
│   │   │       └── [slug]/
│   │   │           ├── page.tsx                     # Org dashboard
│   │   │           ├── settings/page.tsx            # Org settings
│   │   │           └── project/
│   │   │               └── [projectId]/page.tsx     # Project detail (tabs)
│   ├── components/
│   │   ├── ui/                                      # shadcn/ui components
│   │   ├── layout/
│   │   │   ├── sidebar.tsx
│   │   │   └── header.tsx
│   │   ├── auth/
│   │   │   └── auth-provider.tsx                    # Auth context, token management
│   │   ├── org/
│   │   │   ├── project-card.tsx
│   │   │   ├── activity-feed.tsx
│   │   │   └── member-list.tsx
│   │   ├── project/
│   │   │   ├── overview-tab.tsx
│   │   │   ├── kanban-board.tsx
│   │   │   ├── kanban-column.tsx
│   │   │   ├── kanban-card.tsx
│   │   │   ├── github-tab.tsx
│   │   │   ├── team-tab.tsx
│   │   │   └── issues-tab.tsx
│   │   └── task/
│   │       └── task-modal.tsx
│   ├── lib/
│   │   ├── api.ts                                   # Axios instance, interceptors
│   │   └── utils.ts                                 # cn(), date formatters
│   └── hooks/
│       ├── use-auth.ts
│       ├── use-orgs.ts
│       ├── use-projects.ts
│       ├── use-tasks.ts
│       └── use-github.ts
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
└── Dockerfile
```

### Root

```
pmai/
├── docker-compose.yml         # postgres + backend + frontend
├── .env.example               # environment variable template
├── backend/
├── frontend/
└── docs/
```

---

## Task 1: Project Scaffolding + Docker

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/Dockerfile`

- [ ] **Step 1: Create `.env.example`**

```env
# Database
DATABASE_URL=postgresql+asyncpg://pmai:pmai@localhost:5432/pmai

# GitHub OAuth
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# GitHub App
GITHUB_APP_ID=
GITHUB_APP_PRIVATE_KEY=
GITHUB_WEBHOOK_SECRET=

# JWT
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GITHUB_CLIENT_ID=
```

- [ ] **Step 2: Create `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.35
asyncpg==0.29.0
alembic==1.13.0
pydantic-settings==2.5.0
python-jose[cryptography]==3.3.0
httpx==0.27.0
python-multipart==0.0.9
pytest==8.3.0
pytest-asyncio==0.24.0
```

- [ ] **Step 3: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://pmai:pmai@localhost:5432/pmai"

    github_client_id: str = ""
    github_client_secret: str = ""
    github_app_id: str = ""
    github_app_private_key: str = ""
    github_webhook_secret: str = ""

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    frontend_url: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 4: Create `backend/app/database.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session
```

- [ ] **Step 5: Create package `__init__.py` files**

```bash
touch backend/app/__init__.py backend/app/models/__init__.py backend/app/schemas/__init__.py backend/app/routers/__init__.py backend/app/services/__init__.py
```

- [ ] **Step 6: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request

from app.config import settings

app = FastAPI(title="PM Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def structured_error_handler(request: Request, exc: Exception):
    from fastapi.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.status_code, "message": exc.detail}},
        )
    return JSONResponse(status_code=500, content={"error": {"code": 500, "message": "Internal server error"}})


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 8: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: pmai
      POSTGRES_PASSWORD: pmai
      POSTGRES_DB: pmai
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - db
    volumes:
      - ./backend:/app

volumes:
  pgdata:
```

- [ ] **Step 8: Verify Docker Compose boots**

Run: `docker compose up -d db && cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000 &`
Then: `curl http://localhost:8000/api/health`
Expected: `{"status":"ok"}`

- [ ] **Step 9: Commit**

```bash
git add docker-compose.yml .env.example backend/
git commit -m "feat: scaffold backend with FastAPI, Docker Compose, PostgreSQL"
```

---

## Task 2: Database Models + Alembic Migration

**Files:**
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/organization.py`
- Create: `backend/app/models/project.py`
- Create: `backend/app/models/task.py`
- Create: `backend/app/models/pull_request.py`
- Create: `backend/app/models/activity_log.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`

- [ ] **Step 1: Create `backend/app/models/user.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    github_username: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: Create `backend/app/models/organization.py`**

```python
import uuid
from datetime import datetime
import enum

from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OrgRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    github_installation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrgMember(Base):
    __tablename__ = "org_members"

    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[OrgRole] = mapped_column(Enum(OrgRole), default=OrgRole.member)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 3: Create `backend/app/models/project.py`**

```python
import uuid
from datetime import datetime, date
import enum

from sqlalchemy import String, Integer, Text, Date, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    done = "done"


class ProjectRole(str, enum.Enum):
    lead = "lead"
    developer = "developer"
    reviewer = "reviewer"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.active)
    github_repo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    github_repo_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectMember(Base):
    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[ProjectRole] = mapped_column(Enum(ProjectRole), default=ProjectRole.developer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 4: Create `backend/app/models/task.py`**

```python
import uuid
from datetime import datetime, date
import enum

from sqlalchemy import String, Integer, Text, Date, DateTime, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaskStatus(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_assignee", "assignee_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.todo)
    priority: Mapped[TaskPriority] = mapped_column(Enum(TaskPriority), default=TaskPriority.medium)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    github_issue_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 5: Create `backend/app/models/pull_request.py`**

```python
import uuid
from datetime import datetime
import enum

from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PRState(str, enum.Enum):
    open = "open"
    merged = "merged"
    closed = "closed"


class ReviewState(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    changes_requested = "changes_requested"


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        Index("ix_prs_project_state", "project_id", "state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    github_pr_id: Mapped[int] = mapped_column(Integer)
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    state: Mapped[PRState] = mapped_column(Enum(PRState), default=PRState.open)
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_state: Mapped[ReviewState | None] = mapped_column(Enum(ReviewState), nullable=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PullRequestReviewer(Base):
    __tablename__ = "pull_request_reviewers"

    pr_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pull_requests.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    state: Mapped[ReviewState] = mapped_column(Enum(ReviewState), default=ReviewState.pending)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 6: Create `backend/app/models/activity_log.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    __table_args__ = (
        Index("ix_activity_project_created", "project_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 7: Create `backend/app/models/__init__.py`**

```python
from app.models.user import User, RefreshToken
from app.models.organization import Organization, OrgMember, OrgRole
from app.models.project import Project, ProjectMember, ProjectStatus, ProjectRole
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.pull_request import PullRequest, PullRequestReviewer, PRState, ReviewState
from app.models.activity_log import ActivityLog

__all__ = [
    "User", "RefreshToken",
    "Organization", "OrgMember", "OrgRole",
    "Project", "ProjectMember", "ProjectStatus", "ProjectRole",
    "Task", "TaskStatus", "TaskPriority",
    "PullRequest", "PullRequestReviewer", "PRState", "ReviewState",
    "ActivityLog",
]
```

- [ ] **Step 8: Initialize Alembic**

Run: `cd backend && alembic init alembic`

- [ ] **Step 9: Configure `backend/alembic/env.py`**

Update `target_metadata` to use our models:

```python
# At top of env.py, add:
import asyncio
from app.database import Base, engine
from app.models import *  # noqa: F401, F403 — registers all models

target_metadata = Base.metadata

# Replace run_migrations_online() with async version:
def run_migrations_online():
    asyncio.run(run_async_migrations())

async def run_async_migrations():
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
```

- [ ] **Step 10: Update `backend/alembic.ini`**

Set `sqlalchemy.url` to use sync driver for Alembic:

```ini
sqlalchemy.url = postgresql://pmai:pmai@localhost:5432/pmai
```

- [ ] **Step 11: Generate initial migration**

Run: `cd backend && alembic revision --autogenerate -m "initial models"`

- [ ] **Step 12: Apply migration**

Run: `cd backend && alembic upgrade head`

- [ ] **Step 13: Verify tables exist**

Run: `docker compose exec db psql -U pmai -d pmai -c "\dt"`
Expected: All tables listed (users, organizations, org_members, projects, project_members, tasks, pull_requests, pull_request_reviewers, activity_logs, refresh_tokens)

- [ ] **Step 14: Commit**

```bash
git add backend/
git commit -m "feat: add database models and initial Alembic migration"
```

---

## Task 3: Auth System (GitHub OAuth + JWT)

**Files:**
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/dependencies.py`
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`
- Modify: `backend/app/main.py` (register router)

- [ ] **Step 0: Create test database**

Run: `docker compose exec db psql -U pmai -c "CREATE DATABASE pmai_test;"`

- [ ] **Step 1: Write test fixtures in `backend/tests/conftest.py`**

```python
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models.user import User

TEST_DB_URL = "postgresql+asyncpg://pmai:pmai@localhost:5432/pmai_test"

engine_test = create_async_engine(TEST_DB_URL)
async_session_test = async_sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with async_session_test() as session:
        yield session


async def override_get_db():
    async with async_session_test() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        github_id=12345,
        github_username="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="https://github.com/testuser.png",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user):
    from app.services.auth_service import create_access_token
    token = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}
```

- [ ] **Step 2: Create `backend/app/schemas/auth.py`**

```python
import uuid
from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    github_id: int
    github_username: str
    name: str
    email: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Create `backend/app/services/auth_service.py`**

```python
import uuid
from datetime import datetime, timedelta

import httpx
from jose import jwt
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User, RefreshToken

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except Exception:
        return None


def get_github_auth_url(state: str) -> str:
    return f"{GITHUB_AUTH_URL}?client_id={settings.github_client_id}&state={state}&scope=read:user,user:email"


async def exchange_github_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_TOKEN_URL,
            json={"client_id": settings.github_client_id, "client_secret": settings.github_client_secret, "code": code},
            headers={"Accept": "application/json"},
        )
        return resp.json()


async def get_github_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(GITHUB_USER_URL, headers={"Authorization": f"Bearer {access_token}"})
        return resp.json()


async def upsert_user(db: AsyncSession, github_user: dict) -> User:
    result = await db.execute(select(User).where(User.github_id == github_user["id"]))
    user = result.scalar_one_or_none()

    if user:
        user.github_username = github_user["login"]
        user.name = github_user.get("name") or github_user["login"]
        user.email = github_user.get("email")
        user.avatar_url = github_user.get("avatar_url")
        user.updated_at = datetime.utcnow()
    else:
        user = User(
            github_id=github_user["id"],
            github_username=github_user["login"],
            name=github_user.get("name") or github_user["login"],
            email=github_user.get("email"),
            avatar_url=github_user.get("avatar_url"),
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return user


async def save_refresh_token(db: AsyncSession, user_id: uuid.UUID, token: str) -> None:
    expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    db.add(RefreshToken(user_id=user_id, token=token, expires_at=expires_at))
    await db.commit()


async def validate_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == token, RefreshToken.expires_at > datetime.utcnow())
    )
    return result.scalar_one_or_none()


async def delete_refresh_token(db: AsyncSession, token: str) -> None:
    await db.execute(delete(RefreshToken).where(RefreshToken.token == token))
    await db.commit()


async def delete_user_refresh_tokens(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await db.commit()
```

- [ ] **Step 4: Create `backend/app/dependencies.py`**

```python
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.organization import OrgMember, OrgRole
from app.models.project import ProjectMember, ProjectRole
from app.services.auth_service import decode_access_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_org_role(*roles: OrgRole):
    async def checker(
        org_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> OrgMember:
        result = await db.execute(
            select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user.id)
        )
        member = result.scalar_one_or_none()
        if not member or member.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return member
    return checker


def require_project_role(*roles: ProjectRole):
    async def checker(
        project_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> ProjectMember:
        result = await db.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)
        )
        member = result.scalar_one_or_none()
        if not member or member.role not in roles:
            # Check if user is org owner/admin (they have full access)
            from app.models.project import Project
            project = await db.get(Project, project_id)
            if project:
                org_result = await db.execute(
                    select(OrgMember).where(
                        OrgMember.org_id == project.org_id,
                        OrgMember.user_id == user.id,
                        OrgMember.role.in_([OrgRole.owner, OrgRole.admin]),
                    )
                )
                org_member = org_result.scalar_one_or_none()
                if org_member:
                    return org_member  # org admin/owner bypass — returns OrgMember as sentinel
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return member
    return checker
```

- [ ] **Step 5: Create `backend/app/routers/auth.py`**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import TokenResponse, UserResponse
from app.services import auth_service
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/github")
async def github_login():
    state = uuid.uuid4().hex
    url = auth_service.get_github_auth_url(state)
    return RedirectResponse(url=url)


@router.get("/github/callback")
async def github_callback(code: str, state: str, response: Response, db: AsyncSession = Depends(get_db)):
    token_data = await auth_service.exchange_github_code(code)
    gh_access_token = token_data.get("access_token")
    if not gh_access_token:
        raise HTTPException(status_code=400, detail="Failed to get GitHub token")

    github_user = await auth_service.get_github_user(gh_access_token)
    user = await auth_service.upsert_user(db, github_user)

    access_token = auth_service.create_access_token(str(user.id))
    refresh_token = auth_service.create_refresh_token()
    await auth_service.save_refresh_token(db, user.id, refresh_token)

    response = RedirectResponse(url=f"{settings.frontend_url}/auth/callback?access_token={access_token}")
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh(refresh_token: str = Cookie(None), db: AsyncSession = Depends(get_db)):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    token_record = await auth_service.validate_refresh_token(db, refresh_token)
    if not token_record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = auth_service.create_access_token(str(token_record.user_id))
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(response: Response, refresh_token: str = Cookie(None), db: AsyncSession = Depends(get_db)):
    if refresh_token:
        await auth_service.delete_refresh_token(db, refresh_token)
    response.delete_cookie("refresh_token")
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user
```

- [ ] **Step 6: Register auth router in `backend/app/main.py`**

Add to main.py:
```python
from app.routers import auth
app.include_router(auth.router)
```

- [ ] **Step 7: Write auth tests in `backend/tests/test_auth.py`**

```python
import pytest


@pytest.mark.asyncio
async def test_me_unauthorized(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me_authorized(client, auth_headers):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["github_username"] == "testuser"


@pytest.mark.asyncio
async def test_refresh_no_cookie(client):
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(client):
    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 200
```

- [ ] **Step 8: Run tests**

Run: `cd backend && pytest tests/test_auth.py -v`
Expected: All tests pass.

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat: implement GitHub OAuth + JWT auth system"
```

---

## Task 4: Organization CRUD API

**Files:**
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/schemas/organization.py`
- Create: `backend/app/services/org_service.py`
- Create: `backend/app/routers/orgs.py`
- Create: `backend/tests/test_orgs.py`
- Modify: `backend/app/main.py` (register router)

- [ ] **Step 1: Create `backend/app/schemas/common.py`**

```python
from pydantic import BaseModel


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedResponse(BaseModel):
    meta: PaginationMeta
    data: list


class ErrorResponse(BaseModel):
    error: dict  # {"code": "NOT_FOUND", "message": "..."}
```

- [ ] **Step 2: Create `backend/app/schemas/organization.py`**

```python
import uuid
from datetime import datetime
from pydantic import BaseModel

from app.models.organization import OrgRole


class OrgCreate(BaseModel):
    name: str
    slug: str


class OrgUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None


class OrgResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    owner_id: uuid.UUID
    github_installation_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberAdd(BaseModel):
    github_username: str
    role: OrgRole = OrgRole.member


class MemberUpdate(BaseModel):
    role: OrgRole


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    github_username: str
    name: str
    avatar_url: str | None
    role: OrgRole
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Create `backend/app/services/org_service.py`**

```python
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrgMember, OrgRole
from app.models.user import User


async def list_user_orgs(db: AsyncSession, user_id: uuid.UUID) -> list[Organization]:
    result = await db.execute(
        select(Organization)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .where(OrgMember.user_id == user_id)
        .order_by(Organization.created_at.desc())
    )
    return list(result.scalars().all())


async def create_org(db: AsyncSession, user_id: uuid.UUID, name: str, slug: str) -> Organization:
    # Check slug uniqueness
    existing = await db.execute(select(Organization).where(Organization.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already taken")

    org = Organization(name=name, slug=slug, owner_id=user_id)
    db.add(org)
    await db.flush()

    # Add creator as owner
    db.add(OrgMember(org_id=org.id, user_id=user_id, role=OrgRole.owner))
    await db.commit()
    await db.refresh(org)
    return org


async def get_org(db: AsyncSession, org_id: uuid.UUID) -> Organization:
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


async def update_org(db: AsyncSession, org_id: uuid.UUID, name: str | None, slug: str | None) -> Organization:
    org = await get_org(db, org_id)
    if name is not None:
        org.name = name
    if slug is not None:
        existing = await db.execute(select(Organization).where(Organization.slug == slug, Organization.id != org_id))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Slug already taken")
        org.slug = slug
    org.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(org)
    return org


async def list_members(db: AsyncSession, org_id: uuid.UUID) -> list:
    result = await db.execute(
        select(OrgMember, User)
        .join(User, User.id == OrgMember.user_id)
        .where(OrgMember.org_id == org_id)
    )
    return [
        {
            "user_id": member.user_id,
            "github_username": user.github_username,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "role": member.role,
            "created_at": member.created_at,
        }
        for member, user in result.all()
    ]


async def add_member(db: AsyncSession, org_id: uuid.UUID, github_username: str, role: OrgRole) -> dict:
    # Find user by github_username
    result = await db.execute(select(User).where(User.github_username == github_username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. They must sign up first.")

    # Check not already member
    existing = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member")

    member = OrgMember(org_id=org_id, user_id=user.id, role=role)
    db.add(member)
    await db.commit()

    return {
        "user_id": user.id,
        "github_username": user.github_username,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "role": role,
        "created_at": member.created_at,
    }


async def remove_member(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    if member.role == OrgRole.owner:
        raise HTTPException(status_code=400, detail="Cannot remove the owner")
    await db.delete(member)
    await db.commit()

    # Revoke refresh tokens so removed member loses access after current token expires
    from app.services.auth_service import delete_user_refresh_tokens
    await delete_user_refresh_tokens(db, user_id)


async def update_member_role(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, role: OrgRole) -> None:
    result = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member.role = role
    member.updated_at = datetime.utcnow()
    await db.commit()
```

- [ ] **Step 4: Create `backend/app/routers/orgs.py`**

```python
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_org_role
from app.models.user import User
from app.models.organization import OrgRole
from app.schemas.organization import OrgCreate, OrgUpdate, OrgResponse, MemberAdd, MemberUpdate, MemberResponse
from app.services import org_service

router = APIRouter(prefix="/api/orgs", tags=["organizations"])


@router.get("", response_model=list[OrgResponse])
async def list_orgs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await org_service.list_user_orgs(db, user.id)


@router.post("", response_model=OrgResponse, status_code=201)
async def create_org(body: OrgCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await org_service.create_org(db, user.id, body.name, body.slug)


@router.get("/{org_id}", response_model=OrgResponse)
async def get_org(org_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member))):
    return await org_service.get_org(db, org_id)


@router.patch("/{org_id}", response_model=OrgResponse)
async def update_org(org_id: uuid.UUID, body: OrgUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_org_role(OrgRole.owner))):
    return await org_service.update_org(db, org_id, body.name, body.slug)


@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members(org_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member))):
    return await org_service.list_members(db, org_id)


@router.post("/{org_id}/members", response_model=MemberResponse, status_code=201)
async def add_member(org_id: uuid.UUID, body: MemberAdd, db: AsyncSession = Depends(get_db), _=Depends(require_org_role(OrgRole.owner, OrgRole.admin))):
    return await org_service.add_member(db, org_id, body.github_username, body.role)


@router.delete("/{org_id}/members/{user_id}", status_code=204)
async def remove_member(org_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(require_org_role(OrgRole.owner, OrgRole.admin))):
    await org_service.remove_member(db, org_id, user_id)


@router.patch("/{org_id}/members/{user_id}")
async def update_member(org_id: uuid.UUID, user_id: uuid.UUID, body: MemberUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_org_role(OrgRole.owner))):
    await org_service.update_member_role(db, org_id, user_id, body.role)
    return {"ok": True}
```

- [ ] **Step 5: Register router in `backend/app/main.py`**

```python
from app.routers import auth, orgs
app.include_router(auth.router)
app.include_router(orgs.router)
```

- [ ] **Step 6: Write tests in `backend/tests/test_orgs.py`**

```python
import pytest


@pytest.mark.asyncio
async def test_create_org(client, auth_headers):
    resp = await client.post("/api/orgs", json={"name": "My Org", "slug": "my-org"}, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Org"
    assert data["slug"] == "my-org"


@pytest.mark.asyncio
async def test_list_orgs(client, auth_headers):
    await client.post("/api/orgs", json={"name": "Org1", "slug": "org1"}, headers=auth_headers)
    resp = await client.get("/api/orgs", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_duplicate_slug(client, auth_headers):
    await client.post("/api/orgs", json={"name": "Org1", "slug": "dup"}, headers=auth_headers)
    resp = await client.post("/api/orgs", json={"name": "Org2", "slug": "dup"}, headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_org_members(client, auth_headers):
    resp = await client.post("/api/orgs", json={"name": "Org1", "slug": "org1"}, headers=auth_headers)
    org_id = resp.json()["id"]
    resp = await client.get(f"/api/orgs/{org_id}/members", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1  # creator is owner
    assert resp.json()[0]["role"] == "owner"
```

- [ ] **Step 7: Run tests**

Run: `cd backend && pytest tests/test_orgs.py -v`
Expected: All pass.

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: implement organization CRUD with member management"
```

---

## Task 5: Project CRUD + Members API

**Files:**
- Create: `backend/app/schemas/project.py`
- Create: `backend/app/services/project_service.py`
- Create: `backend/app/routers/projects.py`
- Create: `backend/tests/test_projects.py`
- Modify: `backend/app/main.py` (register router)

- [ ] **Step 1: Create `backend/app/schemas/project.py`**

```python
import uuid
from datetime import datetime, date
from pydantic import BaseModel

from app.models.project import ProjectStatus, ProjectRole


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str | None
    status: ProjectStatus
    github_repo_url: str | None
    github_repo_id: int | None
    start_date: date | None
    end_date: date | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectMemberAdd(BaseModel):
    github_username: str
    role: ProjectRole = ProjectRole.developer


class ProjectMemberUpdate(BaseModel):
    role: ProjectRole


class ProjectMemberResponse(BaseModel):
    user_id: uuid.UUID
    github_username: str
    name: str
    avatar_url: str | None
    role: ProjectRole
    created_at: datetime
```

- [ ] **Step 2: Create `backend/app/services/project_service.py`**

```python
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember, ProjectRole
from app.models.organization import OrgMember
from app.models.user import User


async def list_projects(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> list[Project]:
    # Check if org admin/owner — they see all projects
    org_member = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
    )
    member = org_member.scalar_one_or_none()

    if member and member.role in ("owner", "admin"):
        result = await db.execute(
            select(Project).where(Project.org_id == org_id).order_by(Project.created_at.desc())
        )
    else:
        result = await db.execute(
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(Project.org_id == org_id, ProjectMember.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
    return list(result.scalars().all())


async def create_project(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Project:
    project = Project(org_id=org_id, **kwargs)
    db.add(project)
    await db.flush()

    db.add(ProjectMember(project_id=project.id, user_id=user_id, role=ProjectRole.lead))
    await db.commit()
    await db.refresh(project)
    return project


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def update_project(db: AsyncSession, project_id: uuid.UUID, **kwargs) -> Project:
    project = await get_project(db, project_id)
    for key, value in kwargs.items():
        if value is not None:
            setattr(project, key, value)
    project.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> None:
    project = await get_project(db, project_id)
    await db.delete(project)
    await db.commit()


async def list_project_members(db: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
    )
    return [
        {
            "user_id": member.user_id,
            "github_username": user.github_username,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "role": member.role,
            "created_at": member.created_at,
        }
        for member, user in result.all()
    ]


async def add_project_member(db: AsyncSession, project_id: uuid.UUID, github_username: str, role: ProjectRole) -> dict:
    result = await db.execute(select(User).where(User.github_username == github_username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = await db.execute(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a project member")

    member = ProjectMember(project_id=project_id, user_id=user.id, role=role)
    db.add(member)
    await db.commit()

    return {
        "user_id": user.id,
        "github_username": user.github_username,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "role": role,
        "created_at": member.created_at,
    }


async def remove_project_member(db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.delete(member)
    await db.commit()


async def update_project_member_role(db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID, role: ProjectRole) -> None:
    result = await db.execute(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member.role = role
    member.updated_at = datetime.utcnow()
    await db.commit()
```

- [ ] **Step 3: Create `backend/app/routers/projects.py`**

```python
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_org_role
from app.models.user import User
from app.models.organization import OrgRole
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectMemberAdd, ProjectMemberUpdate, ProjectMemberResponse,
)
from app.services import project_service

router = APIRouter(tags=["projects"])


@router.post("/api/orgs/{org_id}/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    org_id: uuid.UUID,
    body: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
):
    return await project_service.create_project(
        db, org_id, user.id, name=body.name, description=body.description,
        start_date=body.start_date, end_date=body.end_date,
    )


@router.get("/api/orgs/{org_id}/projects", response_model=list[ProjectResponse])
async def list_projects(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await project_service.list_projects(db, org_id, user.id)


@router.get("/api/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await project_service.get_project(db, project_id)


@router.patch("/api/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: uuid.UUID, body: ProjectUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_project_role(ProjectRole.lead))):
    return await project_service.update_project(
        db, project_id, name=body.name, description=body.description,
        status=body.status, start_date=body.start_date, end_date=body.end_date,
    )


@router.delete("/api/projects/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(require_org_role(OrgRole.owner, OrgRole.admin))):
    await project_service.delete_project(db, project_id)


@router.get("/api/projects/{project_id}/members", response_model=list[ProjectMemberResponse])
async def list_members(project_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await project_service.list_project_members(db, project_id)


@router.post("/api/projects/{project_id}/members", response_model=ProjectMemberResponse, status_code=201)
async def add_member(project_id: uuid.UUID, body: ProjectMemberAdd, db: AsyncSession = Depends(get_db), _=Depends(require_project_role(ProjectRole.lead))):
    return await project_service.add_project_member(db, project_id, body.github_username, body.role)


@router.delete("/api/projects/{project_id}/members/{user_id}", status_code=204)
async def remove_member(project_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession = Depends(get_db), _=Depends(require_project_role(ProjectRole.lead))):
    await project_service.remove_project_member(db, project_id, user_id)


@router.patch("/api/projects/{project_id}/members/{user_id}")
async def update_member(project_id: uuid.UUID, user_id: uuid.UUID, body: ProjectMemberUpdate, db: AsyncSession = Depends(get_db), _=Depends(require_project_role(ProjectRole.lead))):
    await project_service.update_project_member_role(db, project_id, user_id, body.role)
    return {"ok": True}
```

- [ ] **Step 4: Register router and write tests**

Add `from app.routers import projects` and `app.include_router(projects.router)` to main.py.

Write `backend/tests/test_projects.py` with tests for:
- Create project → 201
- List projects in org → returns created project
- Update project → changed fields
- Delete project → 204
- Add/remove project member

- [ ] **Step 5: Run tests**

Run: `cd backend && pytest tests/test_projects.py -v`
Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: implement project CRUD with member management"
```

---

## Task 6: Task CRUD API

**Files:**
- Create: `backend/app/schemas/task.py`
- Create: `backend/app/services/task_service.py`
- Create: `backend/app/routers/tasks.py`
- Create: `backend/tests/test_tasks.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/schemas/task.py`**

```python
import uuid
from datetime import datetime, date
from pydantic import BaseModel

from app.models.task import TaskStatus, TaskPriority


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    assignee_id: uuid.UUID | None = None
    priority: TaskPriority = TaskPriority.medium
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_id: uuid.UUID | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    assignee_id: uuid.UUID | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    github_issue_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create `backend/app/services/task_service.py`**

```python
import uuid
import math
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskPriority


async def create_task(db: AsyncSession, project_id: uuid.UUID, **kwargs) -> Task:
    task = Task(project_id=project_id, **kwargs)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def list_tasks(
    db: AsyncSession,
    project_id: uuid.UUID,
    status: TaskStatus | None = None,
    assignee_id: uuid.UUID | None = None,
    priority: TaskPriority | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    query = select(Task).where(Task.project_id == project_id)
    count_query = select(func.count(Task.id)).where(Task.project_id == project_id)

    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)
        count_query = count_query.where(Task.assignee_id == assignee_id)
    if priority:
        query = query.where(Task.priority == priority)
        count_query = count_query.where(Task.priority == priority)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Task.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)

    return {
        "data": list(result.scalars().all()),
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total / per_page) if total > 0 else 0,
        },
    }


async def get_task(db: AsyncSession, task_id: uuid.UUID) -> Task:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def update_task(db: AsyncSession, task_id: uuid.UUID, **kwargs) -> Task:
    task = await get_task(db, task_id)
    for key, value in kwargs.items():
        if value is not None:
            setattr(task, key, value)
    task.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task_id: uuid.UUID) -> None:
    task = await get_task(db, task_id)
    await db.delete(task)
    await db.commit()
```

- [ ] **Step 3: Create `backend/app/routers/tasks.py`**

```python
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.task import TaskStatus, TaskPriority
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services import task_service

router = APIRouter(tags=["tasks"])


@router.post("/api/projects/{project_id}/tasks", response_model=TaskResponse, status_code=201)
async def create_task(project_id: uuid.UUID, body: TaskCreate, db: AsyncSession = Depends(get_db)):
    return await task_service.create_task(
        db, project_id, title=body.title, description=body.description,
        assignee_id=body.assignee_id, priority=body.priority, due_date=body.due_date,
    )


@router.get("/api/projects/{project_id}/tasks")
async def list_tasks(
    project_id: uuid.UUID,
    status: TaskStatus | None = None,
    assignee_id: uuid.UUID | None = None,
    priority: TaskPriority | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await task_service.list_tasks(db, project_id, status, assignee_id, priority, page, per_page)


@router.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await task_service.get_task(db, task_id)


@router.patch("/api/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: uuid.UUID, body: TaskUpdate, db: AsyncSession = Depends(get_db)):
    return await task_service.update_task(
        db, task_id, title=body.title, description=body.description,
        assignee_id=body.assignee_id, status=body.status, priority=body.priority,
        due_date=body.due_date,
    )


@router.delete("/api/tasks/{task_id}", status_code=204)
async def delete_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await task_service.delete_task(db, task_id)
```

- [ ] **Step 4: Register router, write tests, run, commit**

Same pattern: register in main.py, test CRUD + pagination + filters, verify, commit.

```bash
git commit -m "feat: implement task CRUD with pagination and filtering"
```

---

## Task 7: GitHub Webhook Integration

**Files:**
- Create: `backend/app/services/github_service.py`
- Create: `backend/app/routers/github.py`
- Create: `backend/app/schemas/pull_request.py`
- Create: `backend/app/schemas/activity_log.py`
- Create: `backend/tests/test_github.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/services/github_service.py`**

```python
import hashlib
import hmac
import uuid
from datetime import datetime

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.models.project import Project
from app.models.pull_request import PullRequest, PullRequestReviewer, PRState, ReviewState
from app.models.task import Task, TaskStatus
from app.models.activity_log import ActivityLog


async def verify_webhook_signature(request: Request) -> bytes:
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    return body


async def resolve_github_user(db: AsyncSession, github_user: dict) -> uuid.UUID | None:
    if not github_user:
        return None
    result = await db.execute(select(User).where(User.github_id == github_user["id"]))
    user = result.scalar_one_or_none()
    return user.id if user else None


async def find_project_by_repo_id(db: AsyncSession, repo_id: int) -> Project | None:
    result = await db.execute(select(Project).where(Project.github_repo_id == repo_id))
    return result.scalar_one_or_none()


async def handle_pull_request(db: AsyncSession, payload: dict) -> None:
    repo_id = payload["repository"]["id"]
    project = await find_project_by_repo_id(db, repo_id)
    if not project:
        return

    pr_data = payload["pull_request"]
    action = payload["action"]
    author_id = await resolve_github_user(db, pr_data.get("user"))

    # Map GitHub state
    if pr_data.get("merged"):
        state = PRState.merged
    elif pr_data["state"] == "closed":
        state = PRState.closed
    else:
        state = PRState.open

    # Upsert PR
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.project_id == project.id,
            PullRequest.github_pr_id == pr_data["id"],
        )
    )
    pr = result.scalar_one_or_none()

    if pr:
        pr.title = pr_data["title"]
        pr.state = state
        pr.merged_at = datetime.fromisoformat(pr_data["merged_at"].replace("Z", "+00:00")) if pr_data.get("merged_at") else None
        pr.updated_at = datetime.utcnow()
    else:
        pr = PullRequest(
            project_id=project.id,
            github_pr_id=pr_data["id"],
            number=pr_data["number"],
            title=pr_data["title"],
            state=state,
            author_id=author_id,
            merged_at=datetime.fromisoformat(pr_data["merged_at"].replace("Z", "+00:00")) if pr_data.get("merged_at") else None,
        )
        db.add(pr)

    # Sync requested reviewers
    for reviewer in pr_data.get("requested_reviewers", []):
        reviewer_id = await resolve_github_user(db, reviewer)
        if reviewer_id:
            existing = await db.execute(
                select(PullRequestReviewer).where(
                    PullRequestReviewer.pr_id == pr.id,
                    PullRequestReviewer.user_id == reviewer_id,
                )
            )
            if not existing.scalar_one_or_none():
                db.add(PullRequestReviewer(pr_id=pr.id, user_id=reviewer_id))

    # Activity log
    db.add(ActivityLog(
        project_id=project.id,
        user_id=author_id,
        action=f"pr_{action}",
        detail={"pr_number": pr_data["number"], "title": pr_data["title"], "github_username": pr_data["user"]["login"]},
    ))

    await db.commit()


async def handle_issues(db: AsyncSession, payload: dict) -> None:
    repo_id = payload["repository"]["id"]
    project = await find_project_by_repo_id(db, repo_id)
    if not project:
        return

    issue = payload["issue"]
    action = payload["action"]
    user_id = await resolve_github_user(db, issue.get("user"))

    if action == "opened":
        # Create task linked to issue
        task = Task(
            project_id=project.id,
            title=issue["title"],
            description=issue.get("body"),
            github_issue_id=issue["id"],
            status=TaskStatus.todo,
        )
        if issue.get("assignee"):
            assignee_id = await resolve_github_user(db, issue["assignee"])
            task.assignee_id = assignee_id
        db.add(task)
    elif action == "closed":
        result = await db.execute(
            select(Task).where(Task.github_issue_id == issue["id"])
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = TaskStatus.done
            task.updated_at = datetime.utcnow()
    elif action == "edited":
        result = await db.execute(
            select(Task).where(Task.github_issue_id == issue["id"])
        )
        task = result.scalar_one_or_none()
        if task:
            task.title = issue["title"]
            task.description = issue.get("body")
            task.updated_at = datetime.utcnow()

    db.add(ActivityLog(
        project_id=project.id,
        user_id=user_id,
        action=f"issue_{action}",
        detail={"issue_number": issue["number"], "title": issue["title"], "github_username": issue["user"]["login"]},
    ))

    await db.commit()


async def handle_push(db: AsyncSession, payload: dict) -> None:
    repo_id = payload["repository"]["id"]
    project = await find_project_by_repo_id(db, repo_id)
    if not project:
        return

    pusher_name = payload.get("pusher", {}).get("name", "unknown")
    commits = payload.get("commits", [])

    db.add(ActivityLog(
        project_id=project.id,
        action="push",
        detail={
            "ref": payload.get("ref"),
            "pusher": pusher_name,
            "commits": [{"sha": c["id"][:7], "message": c["message"]} for c in commits[:10]],
        },
    ))

    await db.commit()


async def handle_pull_request_review(db: AsyncSession, payload: dict) -> None:
    repo_id = payload["repository"]["id"]
    project = await find_project_by_repo_id(db, repo_id)
    if not project:
        return

    review = payload["review"]
    pr_data = payload["pull_request"]
    reviewer_id = await resolve_github_user(db, review.get("user"))

    # Find PR
    result = await db.execute(
        select(PullRequest).where(
            PullRequest.project_id == project.id,
            PullRequest.github_pr_id == pr_data["id"],
        )
    )
    pr = result.scalar_one_or_none()
    if not pr:
        return

    # Map review state
    state_map = {"approved": ReviewState.approved, "changes_requested": ReviewState.changes_requested}
    review_state = state_map.get(review["state"], ReviewState.pending)

    # Upsert reviewer
    if reviewer_id:
        existing = await db.execute(
            select(PullRequestReviewer).where(
                PullRequestReviewer.pr_id == pr.id,
                PullRequestReviewer.user_id == reviewer_id,
            )
        )
        pr_reviewer = existing.scalar_one_or_none()
        if pr_reviewer:
            pr_reviewer.state = review_state
            pr_reviewer.submitted_at = datetime.utcnow()
        else:
            db.add(PullRequestReviewer(
                pr_id=pr.id, user_id=reviewer_id,
                state=review_state, submitted_at=datetime.utcnow(),
            ))

    # Update PR overall review state
    pr.review_state = review_state
    pr.updated_at = datetime.utcnow()

    db.add(ActivityLog(
        project_id=project.id,
        user_id=reviewer_id,
        action="pr_review_submitted",
        detail={"pr_number": pr_data["number"], "state": review["state"], "github_username": review["user"]["login"]},
    ))

    await db.commit()
```

- [ ] **Step 2: Create `backend/app/schemas/pull_request.py`**

```python
import uuid
from datetime import datetime
from pydantic import BaseModel

from app.models.pull_request import PRState, ReviewState


class PRResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    github_pr_id: int
    number: int
    title: str
    state: PRState
    author_id: uuid.UUID | None
    review_state: ReviewState | None
    merged_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Create `backend/app/schemas/activity_log.py`**

```python
import uuid
from datetime import datetime
from pydantic import BaseModel


class ActivityResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    detail: dict
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Create `backend/app/routers/github.py`**

```python
import json
import uuid

from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.pull_request import PullRequest
from app.models.activity_log import ActivityLog
from app.schemas.pull_request import PRResponse
from app.schemas.activity_log import ActivityResponse
from app.services import github_service

router = APIRouter(tags=["github"])

EVENT_HANDLERS = {
    "pull_request": github_service.handle_pull_request,
    "issues": github_service.handle_issues,
    "push": github_service.handle_push,
    "pull_request_review": github_service.handle_pull_request_review,
}


@router.post("/api/webhooks/github")
async def github_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await github_service.verify_webhook_signature(request)
    event = request.headers.get("X-GitHub-Event")
    payload = json.loads(body)

    handler = EVENT_HANDLERS.get(event)
    if handler:
        await handler(db, payload)

    return {"ok": True}


@router.get("/api/projects/{project_id}/pulls", response_model=list[PRResponse])
async def list_pulls(
    project_id: uuid.UUID,
    state: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(PullRequest).where(PullRequest.project_id == project_id)
    if state:
        query = query.where(PullRequest.state == state)
    query = query.order_by(PullRequest.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/api/projects/{project_id}/activity", response_model=list[ActivityResponse])
async def list_activity(
    project_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(ActivityLog).where(ActivityLog.project_id == project_id)
    if cursor:
        from datetime import datetime
        query = query.where(ActivityLog.created_at < datetime.fromisoformat(cursor))
    query = query.order_by(ActivityLog.created_at.desc()).limit(limit)
    result = await db.execute(query)
    items = list(result.scalars().all())
    next_cursor = items[-1].created_at.isoformat() if items else None
    return {"data": items, "next_cursor": next_cursor}
```

- [ ] **Step 5: Register router, write webhook tests, run, commit**

Test with mock webhook payloads (PR opened, issue opened, push, review).

```bash
git commit -m "feat: implement GitHub webhook processing and PR/activity endpoints"
```

---

## Task 8: GitHub Repo Connection Endpoint

**Files:**
- Modify: `backend/app/services/github_service.py` (add connection + initial sync)
- Modify: `backend/app/routers/projects.py` (add endpoint)
- Create: `backend/tests/test_github_connection.py`

- [ ] **Step 1: Add connection logic to `github_service.py`**

```python
import httpx
from app.config import settings
from app.models.project import Project
from app.models.pull_request import PullRequest, PRState
from app.models.task import Task, TaskStatus


async def connect_github_repo(db: AsyncSession, project_id: uuid.UUID, repo_url: str) -> Project:
    """Parse repo URL, store repo info, trigger initial sync."""
    # Parse owner/repo from URL (e.g., https://github.com/owner/repo)
    parts = repo_url.rstrip("/").split("/")
    owner, repo_name = parts[-2], parts[-1]

    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get repo ID from GitHub API using the org's installation token
    org = await db.get(Organization, project.org_id)
    if not org or not org.github_installation_id:
        raise HTTPException(status_code=400, detail="GitHub App not installed for this organization")

    # Get installation access token
    installation_token = await get_installation_token(org.github_installation_id)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo_name}",
            headers={"Authorization": f"Bearer {installation_token}", "Accept": "application/vnd.github+json"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="GitHub repo not found or no access")
        repo_data = resp.json()

    project.github_repo_url = repo_url
    project.github_repo_id = repo_data["id"]
    project.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(project)

    # Trigger initial sync in background
    import asyncio
    asyncio.create_task(initial_sync(db, project, owner, repo_name, installation_token))

    return project


async def get_installation_token(installation_id: int) -> str:
    """Get a short-lived installation access token from GitHub."""
    import time
    from jose import jwt as jose_jwt

    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 600, "iss": settings.github_app_id}
    jwt_token = jose_jwt.encode(payload, settings.github_app_private_key, algorithm="RS256")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={"Authorization": f"Bearer {jwt_token}", "Accept": "application/vnd.github+json"},
        )
        return resp.json()["token"]


async def initial_sync(db_session_factory, project, owner, repo_name, token):
    """Background task: sync existing PRs and issues from GitHub."""
    from app.database import async_session

    async with async_session() as db:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}

            # Sync open PRs
            resp = await client.get(f"https://api.github.com/repos/{owner}/{repo_name}/pulls?state=all&per_page=100", headers=headers)
            if resp.status_code == 200:
                for pr_data in resp.json():
                    author_id = await resolve_github_user(db, pr_data.get("user"))
                    state = PRState.merged if pr_data.get("merged_at") else (PRState.closed if pr_data["state"] == "closed" else PRState.open)
                    existing = await db.execute(
                        select(PullRequest).where(PullRequest.project_id == project.id, PullRequest.github_pr_id == pr_data["id"])
                    )
                    if not existing.scalar_one_or_none():
                        db.add(PullRequest(
                            project_id=project.id, github_pr_id=pr_data["id"], number=pr_data["number"],
                            title=pr_data["title"], state=state, author_id=author_id,
                        ))

            # Sync open issues
            resp = await client.get(f"https://api.github.com/repos/{owner}/{repo_name}/issues?state=all&per_page=100", headers=headers)
            if resp.status_code == 200:
                for issue_data in resp.json():
                    if issue_data.get("pull_request"):
                        continue  # skip PRs listed as issues
                    existing = await db.execute(
                        select(Task).where(Task.project_id == project.id, Task.github_issue_id == issue_data["id"])
                    )
                    if not existing.scalar_one_or_none():
                        assignee_id = await resolve_github_user(db, issue_data.get("assignee"))
                        db.add(Task(
                            project_id=project.id, title=issue_data["title"],
                            description=issue_data.get("body"), github_issue_id=issue_data["id"],
                            status=TaskStatus.done if issue_data["state"] == "closed" else TaskStatus.todo,
                            assignee_id=assignee_id,
                        ))

            await db.commit()
```

Note: If initial sync is interrupted (e.g., server restart), reconnecting the repo triggers a fresh sync.

- [ ] **Step 2: Add endpoint to `routers/projects.py`**

```python
from pydantic import BaseModel

class GitHubConnect(BaseModel):
    repo_url: str

@router.post("/api/projects/{project_id}/github", response_model=ProjectResponse)
async def connect_github(
    project_id: uuid.UUID,
    body: GitHubConnect,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_project_role(ProjectRole.lead)),
):
    from app.services.github_service import connect_github_repo
    return await connect_github_repo(db, project_id, body.repo_url)
```

- [ ] **Step 3: Write tests**

Test with mocked GitHub API responses: successful connection, repo not found, duplicate repo_id.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: implement GitHub repo connection endpoint with initial sync"
```

---

## Task 9: Dashboard APIs

**Files:**
- Create: `backend/app/schemas/dashboard.py`
- Create: `backend/app/services/dashboard_service.py`
- Create: `backend/app/routers/dashboard.py`
- Create: `backend/tests/test_dashboard.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create `backend/app/schemas/dashboard.py`**

```python
import uuid
from datetime import datetime, date
from pydantic import BaseModel

from app.models.task import TaskStatus, TaskPriority
from app.models.project import ProjectStatus


class StatusDistribution(BaseModel):
    todo: int = 0
    in_progress: int = 0
    review: int = 0
    done: int = 0
    total: int = 0
    progress: float = 0.0


class ProjectSummary(BaseModel):
    id: uuid.UUID
    name: str
    status: ProjectStatus
    progress: StatusDistribution
    member_count: int

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    projects: list[ProjectSummary]
    total_projects: int


class ProgressResponse(BaseModel):
    project_id: uuid.UUID
    distribution: StatusDistribution


class IssueItem(BaseModel):
    type: str  # overdue_task, stale_pr, pending_review, unassigned_task
    title: str
    detail: dict


class IssuesResponse(BaseModel):
    items: list[IssueItem]
    total: int
```

- [ ] **Step 2: Create `backend/app/services/dashboard_service.py`**

```python
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.models.project import Project, ProjectMember
from app.models.pull_request import PullRequest, PullRequestReviewer, PRState, ReviewState
from app.models.organization import OrgMember


async def get_task_distribution(db: AsyncSession, project_id: uuid.UUID) -> dict:
    result = await db.execute(
        select(Task.status, func.count(Task.id))
        .where(Task.project_id == project_id)
        .group_by(Task.status)
    )
    counts = {row[0].value: row[1] for row in result.all()}
    total = sum(counts.values())
    done = counts.get("done", 0)
    return {
        "todo": counts.get("todo", 0),
        "in_progress": counts.get("in_progress", 0),
        "review": counts.get("review", 0),
        "done": done,
        "total": total,
        "progress": round((done / total * 100), 1) if total > 0 else 0.0,
    }


async def get_org_dashboard(db: AsyncSession, org_id: uuid.UUID) -> dict:
    projects_result = await db.execute(
        select(Project).where(Project.org_id == org_id).order_by(Project.created_at.desc())
    )
    projects = projects_result.scalars().all()

    summaries = []
    for project in projects:
        distribution = await get_task_distribution(db, project.id)
        member_count_result = await db.execute(
            select(func.count()).select_from(ProjectMember).where(ProjectMember.project_id == project.id)
        )
        member_count = member_count_result.scalar() or 0
        summaries.append({
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "progress": distribution,
            "member_count": member_count,
        })

    return {"projects": summaries, "total_projects": len(summaries)}


async def get_project_progress(db: AsyncSession, project_id: uuid.UUID) -> dict:
    distribution = await get_task_distribution(db, project_id)
    return {"project_id": project_id, "distribution": distribution}


async def get_my_tasks(db: AsyncSession, user_id: uuid.UUID, page: int = 1, per_page: int = 20) -> dict:
    import math
    query = select(Task).where(Task.assignee_id == user_id, Task.status != TaskStatus.done)
    count_result = await db.execute(
        select(func.count(Task.id)).where(Task.assignee_id == user_id, Task.status != TaskStatus.done)
    )
    total = count_result.scalar() or 0
    result = await db.execute(query.order_by(Task.due_date.asc().nullslast()).offset((page - 1) * per_page).limit(per_page))
    return {
        "data": list(result.scalars().all()),
        "meta": {"total": total, "page": page, "per_page": per_page, "total_pages": math.ceil(total / per_page) if total > 0 else 0},
    }


async def get_project_issues(db: AsyncSession, project_id: uuid.UUID) -> dict:
    now = datetime.utcnow()
    items = []

    # Overdue tasks
    overdue_result = await db.execute(
        select(Task).where(
            Task.project_id == project_id,
            Task.due_date < now.date(),
            Task.status != TaskStatus.done,
        )
    )
    for task in overdue_result.scalars():
        items.append({"type": "overdue_task", "title": task.title, "detail": {"task_id": str(task.id), "due_date": str(task.due_date)}})

    # Stale PRs (open > 7 days)
    stale_result = await db.execute(
        select(PullRequest).where(
            PullRequest.project_id == project_id,
            PullRequest.state == PRState.open,
            PullRequest.created_at < now - timedelta(days=7),
        )
    )
    for pr in stale_result.scalars():
        items.append({"type": "stale_pr", "title": pr.title, "detail": {"pr_id": str(pr.id), "number": pr.number}})

    # Pending reviews (> 3 days)
    pending_result = await db.execute(
        select(PullRequest).where(
            PullRequest.project_id == project_id,
            PullRequest.state == PRState.open,
            PullRequest.created_at < now - timedelta(days=3),
            PullRequest.review_state == ReviewState.pending,
        )
    )
    for pr in pending_result.scalars():
        items.append({"type": "pending_review", "title": pr.title, "detail": {"pr_id": str(pr.id), "number": pr.number}})

    # Unassigned tasks
    unassigned_result = await db.execute(
        select(Task).where(
            Task.project_id == project_id,
            Task.assignee_id.is_(None),
            Task.status != TaskStatus.done,
        )
    )
    for task in unassigned_result.scalars():
        items.append({"type": "unassigned_task", "title": task.title, "detail": {"task_id": str(task.id)}})

    return {"items": items, "total": len(items)}
```

- [ ] **Step 3: Create `backend/app/routers/dashboard.py`**

```python
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardResponse, ProgressResponse, IssuesResponse
from app.schemas.task import TaskResponse
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get("/api/orgs/{org_id}/dashboard", response_model=DashboardResponse)
async def org_dashboard(org_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_org_dashboard(db, org_id)


@router.get("/api/me/tasks")
async def my_tasks(
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await dashboard_service.get_my_tasks(db, user.id, page, per_page)


@router.get("/api/projects/{project_id}/progress", response_model=ProgressResponse)
async def project_progress(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_project_progress(db, project_id)


@router.get("/api/projects/{project_id}/issues", response_model=IssuesResponse)
async def project_issues(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_project_issues(db, project_id)
```

- [ ] **Step 4: Register router, write tests, run, commit**

Test progress calculation (0 tasks = 0%, mixed statuses = correct %), issue detection with edge cases.

```bash
git commit -m "feat: implement dashboard APIs with progress and issue detection"
```

---

## Task 10: Frontend Scaffolding

**Files:**
- Create: `frontend/` (via create-next-app)
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/utils.ts`
- Modify: `docker-compose.yml` (add frontend service)

- [ ] **Step 1: Initialize Next.js project**

```bash
cd /Users/kimjihun/Desktop/pmai
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --no-turbopack
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install @tanstack/react-query axios @dnd-kit/core @dnd-kit/sortable
npx shadcn@latest init
npx shadcn@latest add button card dialog dropdown-menu input badge tabs avatar separator scroll-area
```

- [ ] **Step 3: Create `frontend/src/lib/api.ts`**

```typescript
import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? sessionStorage.getItem("access_token") : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        const { data } = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/auth/refresh`,
          {},
          { withCredentials: true }
        );
        sessionStorage.setItem("access_token", data.access_token);
        error.config.headers.Authorization = `Bearer ${data.access_token}`;
        return axios(error.config);
      } catch {
        sessionStorage.removeItem("access_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

- [ ] **Step 4: Create `frontend/src/lib/utils.ts`**

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString("ko-KR");
}

export function daysAgo(date: string | Date): number {
  const diff = Date.now() - new Date(date).getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24));
}
```

- [ ] **Step 5: Add frontend to `docker-compose.yml`**

```yaml
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
    volumes:
      - ./frontend/src:/app/src
```

- [ ] **Step 6: Create `frontend/Dockerfile`**

```dockerfile
FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

CMD ["npm", "run", "dev"]
```

- [ ] **Step 7: Verify frontend boots**

Run: `cd frontend && npm run dev`
Expected: Next.js dev server on localhost:3000

- [ ] **Step 8: Commit**

```bash
git add frontend/ docker-compose.yml
git commit -m "feat: scaffold Next.js frontend with shadcn/ui and API client"
```

---

## Task 11: Frontend Auth Flow

**Files:**
- Create: `frontend/src/components/auth/auth-provider.tsx`
- Create: `frontend/src/hooks/use-auth.ts`
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/app/auth/callback/page.tsx`
- Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Create auth provider and hook**

`auth-provider.tsx`: React context wrapping the app. Stores access token in sessionStorage. Provides `user`, `login()`, `logout()`, `isLoading`.

`use-auth.ts`: Hook that calls `GET /api/auth/me` on mount, refreshes token on 401.

- [ ] **Step 2: Create login page**

Simple page with "GitHub으로 로그인" button that redirects to `GET /api/auth/github`.

- [ ] **Step 3: Create callback page**

`/auth/callback` — reads `access_token` from URL params, stores in sessionStorage, redirects to dashboard.

- [ ] **Step 4: Wrap layout with providers**

```tsx
// layout.tsx
import { AuthProvider } from "@/components/auth/auth-provider";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export default function RootLayout({ children }) {
  return (
    <html><body>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientProvider>
    </body></html>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: implement frontend auth flow with GitHub OAuth"
```

---

## Task 12: Frontend Dashboard Layout + Org Dashboard

**Files:**
- Create: `frontend/src/app/(dashboard)/layout.tsx`
- Create: `frontend/src/components/layout/sidebar.tsx`
- Create: `frontend/src/components/layout/header.tsx`
- Create: `frontend/src/hooks/use-orgs.ts`
- Create: `frontend/src/components/org/project-card.tsx`
- Create: `frontend/src/components/org/activity-feed.tsx`
- Create: `frontend/src/app/(dashboard)/org/[slug]/page.tsx`

- [ ] **Step 1: Create dashboard layout with sidebar + header**

Sidebar: org list, org switcher, navigation links (Dashboard, Projects, My Tasks, Settings).
Header: user avatar, logout button.

- [ ] **Step 2: Create `use-orgs.ts` hook**

```typescript
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

export function useOrgs() {
  return useQuery({ queryKey: ["orgs"], queryFn: () => api.get("/api/orgs").then((r) => r.data) });
}

export function useOrgDashboard(orgId: string) {
  return useQuery({
    queryKey: ["org-dashboard", orgId],
    queryFn: () => api.get(`/api/orgs/${orgId}/dashboard`).then((r) => r.data),
    enabled: !!orgId,
  });
}
```

- [ ] **Step 3: Create `project-card.tsx`**

Card showing: project name, status badge, progress bar, member avatars, task count.

- [ ] **Step 4: Create `activity-feed.tsx`**

Scrollable list of recent activities (PR merged, issue created, task completed).

- [ ] **Step 5: Create org dashboard page**

Grid of project cards + activity feed + team overview.

- [ ] **Step 6: Commit**

```bash
git commit -m "feat: implement org dashboard with project cards and activity feed"
```

---

## Task 13: Frontend Project Detail Pages

**Files:**
- Create: `frontend/src/hooks/use-projects.ts`
- Create: `frontend/src/hooks/use-tasks.ts`
- Create: `frontend/src/hooks/use-github.ts`
- Create: `frontend/src/components/project/overview-tab.tsx`
- Create: `frontend/src/components/project/github-tab.tsx`
- Create: `frontend/src/components/project/team-tab.tsx`
- Create: `frontend/src/components/project/issues-tab.tsx`
- Create: `frontend/src/app/(dashboard)/org/[slug]/project/[projectId]/page.tsx`

- [ ] **Step 1: Create data hooks**

`use-projects.ts`: `useProject(id)`, `useProjectMembers(id)`, `useProjectProgress(id)`
`use-tasks.ts`: `useTasks(projectId, filters)`, `useCreateTask()`, `useUpdateTask()`
`use-github.ts`: `usePulls(projectId)`, `useActivity(projectId)`

- [ ] **Step 2: Create overview tab**

Progress bar, status distribution chart, date range, project description.

- [ ] **Step 3: Create GitHub tab**

PR list with state badges (open/merged/closed), review state indicators.
Recent commits from activity log.

- [ ] **Step 4: Create team tab**

Member list with roles, each member's task count.

- [ ] **Step 5: Create issues tab**

Grouped by type: overdue tasks, stale PRs, pending reviews, unassigned tasks.

- [ ] **Step 6: Create project detail page with tab navigation**

```tsx
// Uses shadcn Tabs component
<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="tasks">Tasks</TabsTrigger>
    <TabsTrigger value="github">GitHub</TabsTrigger>
    <TabsTrigger value="team">Team</TabsTrigger>
    <TabsTrigger value="issues">Issues</TabsTrigger>
  </TabsList>
  <TabsContent value="overview"><OverviewTab /></TabsContent>
  <TabsContent value="tasks"><KanbanBoard /></TabsContent>
  <TabsContent value="github"><GitHubTab /></TabsContent>
  <TabsContent value="team"><TeamTab /></TabsContent>
  <TabsContent value="issues"><IssuesTab /></TabsContent>
</Tabs>
```

- [ ] **Step 7: Commit**

```bash
git commit -m "feat: implement project detail pages with tabs"
```

---

## Task 14: Kanban Board

**Files:**
- Create: `frontend/src/components/project/kanban-board.tsx`
- Create: `frontend/src/components/project/kanban-column.tsx`
- Create: `frontend/src/components/project/kanban-card.tsx`
- Create: `frontend/src/components/task/task-modal.tsx`

- [ ] **Step 1: Create kanban card**

Shows: title, priority badge, assignee avatar, due date (red if overdue).

- [ ] **Step 2: Create kanban column**

Column for each status (todo, in_progress, review, done). Shows task count in header. Droppable area.

- [ ] **Step 3: Create kanban board with dnd-kit**

```tsx
import { DndContext, closestCenter } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";

// On drag end: call PATCH /api/tasks/{id} with new status
// Optimistic update via TanStack Query
```

- [ ] **Step 4: Create task modal**

Dialog for creating/editing tasks. Fields: title, description, assignee (dropdown), priority (select), due date (date picker).

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: implement kanban board with drag-and-drop"
```

---

## Task 15: Personal View + Settings

**Files:**
- Create: `frontend/src/app/(dashboard)/me/page.tsx`
- Create: `frontend/src/app/(dashboard)/org/[slug]/settings/page.tsx`
- Create: `frontend/src/components/org/member-list.tsx`

- [ ] **Step 1: Create personal view page**

- My tasks (sorted by due date, grouped by project)
- PRs awaiting my review
- Due today / this week section

Uses: `GET /api/me/tasks`

- [ ] **Step 2: Create settings page**

- Org info form (name, slug)
- Member management table (invite by github_username, role dropdown, remove button)
- GitHub App connection status

- [ ] **Step 3: Create member-list component**

Reusable table: avatar, name, github_username, role badge, actions dropdown (change role, remove).

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: implement personal view and org settings pages"
```

---

## Task 16: GitHub Repo Connection UI

**Files:**
- Modify: `frontend/src/app/(dashboard)/org/[slug]/project/[projectId]/page.tsx`
- Add GitHub connection button/dialog to project settings

- [ ] **Step 1: Add "GitHub 연결" button to project detail**

When no repo is connected: show "GitHub 레포 연결" button.
On click: redirect to GitHub App installation page or repo selection.

- [ ] **Step 2: Show connected repo info**

When connected: show repo name, link to GitHub, last sync time.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: implement GitHub repo connection UI"
```

---

## Task 17: End-to-End Verification

- [ ] **Step 1: Docker Compose full stack test**

```bash
docker compose up --build
```

Verify: backend on :8000, frontend on :3000, postgres on :5432.

- [ ] **Step 2: Manual smoke test flow**

1. Open http://localhost:3000 → login page
2. Click "GitHub으로 로그인" → GitHub OAuth → callback → dashboard
3. Create organization → verify in dashboard
4. Create project → verify card appears
5. Create tasks → verify kanban board
6. Move task via drag-and-drop → verify status changes
7. Check personal view → my tasks appear

- [ ] **Step 3: Run all backend tests**

```bash
cd backend && pytest -v
```

- [ ] **Step 4: Final commit**

```bash
git commit -m "feat: complete Phase 1 — core platform, GitHub integration, dashboard"
```

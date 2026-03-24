# PM Agent Phase 4: Google Calendar + Notion Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bidirectional Google Calendar sync (task deadlines ↔ events, meeting briefings) and bidirectional Notion sync (tasks, documents, briefing pages) with last-write-wins conflict resolution.

**Architecture:** Calendar uses Google Push Notifications for change detection; Notion uses 5-minute polling. Both sync through a shared task hook (`after_task_change`) that triggers outbound sync on every task CRUD. OAuth per-user for Calendar, per-org for Notion.

**Tech Stack:** google-api-python-client, google-auth, notion-client, existing FastAPI + SQLAlchemy + APScheduler stack.

**Spec:** `docs/superpowers/specs/2026-03-24-pm-agent-phase4-design.md`

---

## File Structure

### Backend (new/modified)

```
backend/
├── app/
│   ├── config.py                              # MODIFY: add Google/Notion config
│   ├── main.py                                # MODIFY: register calendar + notion routers
│   ├── scheduler.py                           # MODIFY: add meeting briefing + Notion poll + Calendar watch renewal
│   ├── models/
│   │   ├── __init__.py                        # MODIFY: re-export new models
│   │   ├── calendar.py                        # CREATE: GoogleCalendarConnection, CalendarEventMapping
│   │   └── notion.py                          # CREATE: NotionConnection, NotionDatabaseMapping, NotionTaskMapping
│   ├── schemas/
│   │   ├── calendar.py                        # CREATE
│   │   └── notion.py                          # CREATE
│   ├── services/
│   │   ├── calendar/
│   │   │   ├── __init__.py                    # CREATE
│   │   │   ├── auth.py                        # CREATE: Google OAuth token management
│   │   │   ├── sync.py                        # CREATE: bidirectional event sync
│   │   │   └── briefing.py                    # CREATE: meeting briefing checker
│   │   ├── notion/
│   │   │   ├── __init__.py                    # CREATE
│   │   │   ├── auth.py                        # CREATE: Notion OAuth
│   │   │   ├── sync.py                        # CREATE: bidirectional task sync
│   │   │   └── documents.py                   # CREATE: doc read/write + briefing page creation
│   │   └── task_service.py                    # MODIFY: add after_task_change hook
│   ├── routers/
│   │   ├── calendar.py                        # CREATE
│   │   └── notion.py                          # CREATE
│   └── tests/
│       ├── test_calendar_sync.py              # CREATE
│       ├── test_notion_sync.py                # CREATE
│       ├── test_calendar_router.py            # CREATE
│       └── test_notion_router.py              # CREATE
├── alembic/versions/                          # New migration
├── requirements.txt                           # MODIFY
└── .env.example                               # MODIFY
```

### Frontend (new/modified)

```
frontend/src/
├── hooks/
│   ├── use-calendar.ts                        # CREATE
│   └── use-notion.ts                          # CREATE
├── components/
│   ├── calendar/
│   │   └── calendar-connect.tsx               # CREATE
│   └── notion/
│       ├── notion-connect.tsx                 # CREATE
│       └── database-mapping.tsx               # CREATE
└── app/(dashboard)/
    └── org/[slug]/
        └── settings/page.tsx                  # MODIFY: add Calendar + Notion sections
```

---

## Task 1: Dependencies + Configuration

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py`
- Modify: `.env.example`

- [ ] **Step 1: Update requirements.txt** — add:
```
google-api-python-client>=2.100.0
google-auth>=2.25.0
google-auth-oauthlib>=1.2.0
notion-client>=2.2.0
```

- [ ] **Step 2: Update config.py** — add to Settings:
```python
# Google Calendar
google_client_id: str = ""
google_client_secret: str = ""
google_redirect_uri: str = "http://localhost:8000/api/calendar/oauth/callback"

# Notion
notion_client_id: str = ""
notion_client_secret: str = ""
notion_redirect_uri: str = "http://localhost:8000/api/notion/oauth/callback"
```

- [ ] **Step 3: Update .env.example**

- [ ] **Step 4: Commit**
```bash
git commit -m "feat: add Google Calendar and Notion dependencies and configuration"
```

---

## Task 2: Database Models + Migration

**Files:**
- Create: `backend/app/models/calendar.py`
- Create: `backend/app/models/notion.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create `backend/app/models/calendar.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func

from app.database import Base


class GoogleCalendarConnection(Base):
    __tablename__ = "google_calendar_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    google_email: Mapped[str] = mapped_column(String)
    access_token: Mapped[str] = mapped_column(String)
    refresh_token: Mapped[str] = mapped_column(String)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    calendar_id: Mapped[str] = mapped_column(String, default="primary")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CalendarEventMapping(Base):
    __tablename__ = "calendar_event_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), unique=True)
    google_event_id: Mapped[str] = mapped_column(String)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Create `backend/app/models/notion.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func

from app.database import Base


class NotionConnection(Base):
    __tablename__ = "notion_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), unique=True)
    notion_access_token: Mapped[str] = mapped_column(String)
    notion_workspace_id: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class NotionDatabaseMapping(Base):
    __tablename__ = "notion_database_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True)
    notion_database_id: Mapped[str] = mapped_column(String)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotionTaskMapping(Base):
    __tablename__ = "notion_task_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"), unique=True, nullable=True)
    notion_page_id: Mapped[str] = mapped_column(String, unique=True)
    last_modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 3: Update `__init__.py`, generate and apply migration**

- [ ] **Step 4: Commit**
```bash
git commit -m "feat: add Google Calendar and Notion models with migration"
```

---

## Task 3: Google Calendar Auth + Sync Service

**Files:**
- Create: `backend/app/services/calendar/__init__.py`
- Create: `backend/app/services/calendar/auth.py`
- Create: `backend/app/services/calendar/sync.py`

- [ ] **Step 1: Create `auth.py`** — Google OAuth token management:
- `get_google_credentials(db, user_id)` → build google Credentials from stored tokens, auto-refresh if expired
- `save_google_tokens(db, user_id, credentials, email)` → save/update GoogleCalendarConnection
- Use `google.oauth2.credentials.Credentials` with client_id/secret for refresh

- [ ] **Step 2: Create `sync.py`** — Bidirectional calendar sync:
- `sync_task_to_calendar(db, task)` — create/update/delete calendar event based on task state
- `sync_calendar_to_tasks(db, user_id, changed_events)` — process changed events, update task due_dates
- `setup_calendar_watch(db, user_id)` — register Google Push Notification channel
- `process_calendar_webhook(db, channel_id, resource_id)` — fetch changes via syncToken, dispatch to sync_calendar_to_tasks

Import guard for google API libraries (try/except ImportError).

- [ ] **Step 3: Commit**
```bash
git commit -m "feat: implement Google Calendar auth and bidirectional sync"
```

---

## Task 4: Google Calendar Router

**Files:**
- Create: `backend/app/schemas/calendar.py`
- Create: `backend/app/routers/calendar.py`
- Create: `backend/tests/test_calendar_router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create schemas**
```python
from pydantic import BaseModel

class CalendarStatusResponse(BaseModel):
    connected: bool
    google_email: str | None = None
    calendar_id: str | None = None
```

- [ ] **Step 2: Create router** — endpoints:
- `GET /api/calendar/auth` — redirect to Google OAuth
- `GET /api/calendar/oauth/callback` — exchange code, save tokens
- `GET /api/users/me/calendar/status` — connection status
- `DELETE /api/users/me/calendar/disconnect` — disconnect
- `POST /api/calendar/webhook` — Google Push Notification receiver

- [ ] **Step 3: Register router, write tests, run all tests**

- [ ] **Step 4: Commit**
```bash
git commit -m "feat: implement Google Calendar router with OAuth and webhook"
```

---

## Task 5: Meeting Briefing Service

**Files:**
- Create: `backend/app/services/calendar/briefing.py`
- Modify: `backend/app/scheduler.py`

- [ ] **Step 1: Create `briefing.py`**
- `check_upcoming_meetings()` — scheduled job:
  1. For each user with calendar connection
  2. Query events starting in next 30 minutes
  3. Fuzzy match event title to project name
  4. Check if briefing already sent for this event (ActivityLog)
  5. Trigger Phase 2 AI analysis
  6. Send Slack DM with briefing

- [ ] **Step 2: Add to scheduler.py**
```python
scheduler.add_job(check_upcoming_meetings, CronTrigger(minute="*/15"))
scheduler.add_job(renew_calendar_watches, CronTrigger(hour="*/6"))
```

- [ ] **Step 3: Commit**
```bash
git commit -m "feat: add meeting briefing service with 15-minute scheduler"
```

---

## Task 6: Notion Auth + Sync Service

**Files:**
- Create: `backend/app/services/notion/__init__.py`
- Create: `backend/app/services/notion/auth.py`
- Create: `backend/app/services/notion/sync.py`

- [ ] **Step 1: Create `auth.py`** — Notion OAuth:
- `exchange_notion_code(code)` → POST to Notion token endpoint
- `get_notion_client(db, org_id)` → build notion Client from stored token

- [ ] **Step 2: Create `sync.py`** — Bidirectional task sync:
- `sync_task_to_notion(db, task, project_id)` — create/update Notion page from task
- `poll_notion_changes(db)` — scheduled: query all mapped DBs for recent changes, sync to PM Agent
- `convert_task_to_notion_properties(task)` → dict of Notion property values
- `convert_notion_page_to_task_data(page)` → dict of PM Agent task fields
- Last-write-wins: compare `last_modified_at` vs Notion `last_edited_time`
- Log conflicts to ActivityLog

Import guard for notion_client.

- [ ] **Step 3: Commit**
```bash
git commit -m "feat: implement Notion auth and bidirectional task sync"
```

---

## Task 7: Notion Document Service + Briefing Pages

**Files:**
- Create: `backend/app/services/notion/documents.py`
- Modify: `backend/app/services/ai/worker.py` (briefing → Notion page)

- [ ] **Step 1: Create `documents.py`**
- `read_project_documents(db, project_id)` → fetch Notion pages linked to project, return text content
- `create_briefing_page(db, org_id, briefing)` → create a Notion page with briefing content

- [ ] **Step 2: Modify AI worker** — after briefing completion, create Notion page (best-effort)

- [ ] **Step 3: Commit**
```bash
git commit -m "feat: add Notion document reader and briefing page creation"
```

---

## Task 8: Notion Router

**Files:**
- Create: `backend/app/schemas/notion.py`
- Create: `backend/app/routers/notion.py`
- Create: `backend/tests/test_notion_router.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/scheduler.py` (add Notion polling job)

- [ ] **Step 1: Create schemas**
```python
from pydantic import BaseModel

class NotionStatusResponse(BaseModel):
    connected: bool
    notion_workspace_id: str | None = None

class NotionDatabaseRequest(BaseModel):
    notion_database_id: str

class NotionSyncStatusResponse(BaseModel):
    connected: bool
    notion_database_id: str | None = None
    last_synced_at: str | None = None
```

- [ ] **Step 2: Create router** — endpoints:
- `GET /api/orgs/{org_id}/notion/auth` — Notion OAuth redirect
- `GET /api/notion/oauth/callback` — exchange code, save connection
- `GET /api/orgs/{org_id}/notion/status` — connection status
- `DELETE /api/orgs/{org_id}/notion/disconnect` — disconnect
- `POST /api/projects/{project_id}/notion/database` — map Notion DB
- `DELETE /api/projects/{project_id}/notion/database` — unmap
- `GET /api/projects/{project_id}/notion/sync-status` — sync status
- `POST /api/projects/{project_id}/notion/sync` — manual sync trigger

- [ ] **Step 3: Add Notion polling to scheduler**
```python
scheduler.add_job(poll_notion_changes, CronTrigger(minute="*/5"))
```

- [ ] **Step 4: Register router, write tests, run all tests**

- [ ] **Step 5: Commit**
```bash
git commit -m "feat: implement Notion router with OAuth, DB mapping, and sync"
```

---

## Task 9: Task Sync Hooks

**Files:**
- Modify: `backend/app/services/task_service.py`

- [ ] **Step 1: Add `after_task_change` hook**

```python
async def after_task_change(db, task):
    """Trigger Calendar and Notion sync after task create/update."""
    # Calendar sync
    if task.due_date and task.assignee_id:
        try:
            from app.services.calendar.sync import sync_task_to_calendar
            await sync_task_to_calendar(db, task)
        except Exception:
            pass

    # Notion sync
    try:
        from app.services.notion.sync import sync_task_to_notion
        await sync_task_to_notion(db, task, task.project_id)
    except Exception:
        pass
```

- [ ] **Step 2: Call `after_task_change` in `create_task` and `update_task`**

After the `await db.commit()` in both functions, add:
```python
await after_task_change(db, task)
```

- [ ] **Step 3: Run all tests, commit**
```bash
git commit -m "feat: add Calendar and Notion sync hooks to task service"
```

---

## Task 10: Frontend — Hooks + Settings UI

**Files:**
- Create: `frontend/src/hooks/use-calendar.ts`
- Create: `frontend/src/hooks/use-notion.ts`
- Create: `frontend/src/components/calendar/calendar-connect.tsx`
- Create: `frontend/src/components/notion/notion-connect.tsx`
- Create: `frontend/src/components/notion/database-mapping.tsx`
- Modify: `frontend/src/app/(dashboard)/org/[slug]/settings/page.tsx`

- [ ] **Step 1: Create `use-calendar.ts`**
```typescript
export function useCalendarStatus() {
  return useQuery({ queryKey: ["calendar-status"], queryFn: () => api.get("/api/users/me/calendar/status").then(r => r.data) });
}
export function useCalendarDisconnect() {
  return useMutation({ mutationFn: () => api.delete("/api/users/me/calendar/disconnect") });
}
```

- [ ] **Step 2: Create `use-notion.ts`**
```typescript
export function useNotionStatus(orgId: string) { ... }
export function useNotionDisconnect(orgId: string) { ... }
export function useSetNotionDatabase(projectId: string) { ... }
export function useNotionSyncStatus(projectId: string) { ... }
export function useTriggerNotionSync(projectId: string) { ... }
```

- [ ] **Step 3: Create components**
- `calendar-connect.tsx` — connection status, connect/disconnect buttons
- `notion-connect.tsx` — org-level connection status, connect/disconnect
- `database-mapping.tsx` — project-level DB mapping, sync status, manual sync button

- [ ] **Step 4: Modify settings page** — add Calendar + Notion sections after Slack section

- [ ] **Step 5: Build check**
```bash
cd /Users/kimjihun/Desktop/pmai/frontend && npm run build
```

- [ ] **Step 6: Commit**
```bash
git commit -m "feat: implement Calendar and Notion settings UI in dashboard"
```

---

## Task 11: End-to-End Verification

- [ ] **Step 1: Run all backend tests**
```bash
cd /Users/kimjihun/Desktop/pmai/backend && .venv/bin/python -m pytest -v
```

- [ ] **Step 2: Build frontend**
```bash
cd /Users/kimjihun/Desktop/pmai/frontend && npm run build
```

- [ ] **Step 3: Final commit**
```bash
git commit -m "feat: complete Phase 4 — Google Calendar + Notion Integration"
```

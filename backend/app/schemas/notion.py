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

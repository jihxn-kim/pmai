from pydantic import BaseModel


class CalendarStatusResponse(BaseModel):
    connected: bool
    google_email: str | None = None
    calendar_id: str | None = None

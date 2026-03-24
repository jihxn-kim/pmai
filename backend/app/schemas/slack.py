import uuid
from datetime import datetime

from pydantic import BaseModel


class SlackStatusResponse(BaseModel):
    connected: bool
    slack_team_id: str | None = None
    org_channel_id: str | None = None


class ChannelMappingRequest(BaseModel):
    slack_channel_id: str


class OrgChannelRequest(BaseModel):
    slack_channel_id: str


class UserMappingRequest(BaseModel):
    user_id: uuid.UUID
    slack_user_id: str


class UserMappingResponse(BaseModel):
    user_id: uuid.UUID
    slack_user_id: str
    created_at: datetime
    model_config = {"from_attributes": True}

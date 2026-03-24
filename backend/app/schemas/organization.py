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

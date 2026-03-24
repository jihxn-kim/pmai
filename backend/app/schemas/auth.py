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

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_org_role
from app.models.organization import Organization, OrgMember, OrgRole
from app.models.user import User
from app.schemas.organization import (
    MemberAdd,
    MemberResponse,
    MemberUpdate,
    OrgCreate,
    OrgResponse,
    OrgUpdate,
)
from app.services import org_service

router = APIRouter(prefix="/api/orgs", tags=["orgs"])


@router.get("/", response_model=list[OrgResponse])
async def list_my_orgs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    orgs = await org_service.list_user_orgs(db, current_user.id)
    return orgs


@router.post("/", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_org(
    body: OrgCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org = await org_service.create_org(db, current_user.id, body.name, body.slug)
    return org


@router.get("/{org_id}", response_model=OrgResponse)
async def get_org(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)),
    db: AsyncSession = Depends(get_db),
):
    org = await org_service.get_org(db, org_id)
    return org


@router.patch("/{org_id}", response_model=OrgResponse)
async def update_org(
    org_id: uuid.UUID,
    body: OrgUpdate,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner)),
    db: AsyncSession = Depends(get_db),
):
    org = await org_service.update_org(db, org_id, body.name, body.slug)
    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    # Check user is owner
    member = await db.execute(
        select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user.id)
    )
    m = member.scalar_one_or_none()
    if not m or m.role != OrgRole.owner:
        raise HTTPException(status_code=403, detail="Only the owner can delete the organization")
    await db.delete(org)
    await db.commit()


@router.get("/{org_id}/members", response_model=list[MemberResponse])
async def list_members(
    org_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin, OrgRole.member)),
    db: AsyncSession = Depends(get_db),
):
    members = await org_service.list_members(db, org_id)
    return members


@router.post(
    "/{org_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    org_id: uuid.UUID,
    body: MemberAdd,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    member = await org_service.add_member(db, org_id, body.github_username, body.role)
    return member


@router.delete(
    "/{org_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    await org_service.remove_member(db, org_id, user_id)


@router.patch("/{org_id}/members/{user_id}", response_model=MemberResponse)
async def update_member_role(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    body: MemberUpdate,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner)),
    db: AsyncSession = Depends(get_db),
):
    member = await org_service.update_member_role(db, org_id, user_id, body.role)
    return member

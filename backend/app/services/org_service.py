import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrgMember, OrgRole, Organization
from app.models.user import User
from app.services.auth_service import delete_user_refresh_tokens


async def list_user_orgs(db: AsyncSession, user_id: uuid.UUID) -> list[Organization]:
    result = await db.execute(
        select(Organization)
        .join(OrgMember, OrgMember.org_id == Organization.id)
        .where(OrgMember.user_id == user_id)
    )
    return list(result.scalars().all())


async def create_org(
    db: AsyncSession, user_id: uuid.UUID, name: str, slug: str
) -> Organization:
    # Check slug uniqueness
    existing = await db.execute(select(Organization).where(Organization.slug == slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization slug already exists",
        )

    org = Organization(
        name=name,
        slug=slug,
        owner_id=user_id,
    )
    db.add(org)
    await db.flush()  # flush to get the org.id before adding member

    member = OrgMember(
        org_id=org.id,
        user_id=user_id,
        role=OrgRole.owner,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(member)
    await db.commit()
    await db.refresh(org)
    return org


async def get_org(db: AsyncSession, org_id: uuid.UUID) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return org


async def update_org(
    db: AsyncSession,
    org_id: uuid.UUID,
    name: str | None,
    slug: str | None,
) -> Organization:
    org = await get_org(db, org_id)

    if slug is not None and slug != org.slug:
        existing = await db.execute(select(Organization).where(Organization.slug == slug))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization slug already exists",
            )
        org.slug = slug

    if name is not None:
        org.name = name

    await db.commit()
    await db.refresh(org)
    return org


async def list_members(db: AsyncSession, org_id: uuid.UUID) -> list[dict]:
    result = await db.execute(
        select(OrgMember, User)
        .join(User, User.id == OrgMember.user_id)
        .where(OrgMember.org_id == org_id)
    )
    rows = result.all()
    members = []
    for member, user in rows:
        members.append(
            {
                "user_id": user.id,
                "github_username": user.github_username,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "role": member.role,
                "created_at": member.created_at,
            }
        )
    return members


async def add_member(
    db: AsyncSession,
    org_id: uuid.UUID,
    github_username: str,
    role: OrgRole,
) -> dict:
    # Find user by github_username
    user_result = await db.execute(
        select(User).where(User.github_username == github_username)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check not already a member
    existing = await db.execute(
        select(OrgMember).where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization",
        )

    now = datetime.now(timezone.utc)
    member = OrgMember(
        org_id=org_id,
        user_id=user.id,
        role=role,
        created_at=now,
        updated_at=now,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)

    return {
        "user_id": user.id,
        "github_username": user.github_username,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "role": member.role,
        "created_at": member.created_at,
    }


async def remove_member(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(OrgMember).where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    if member.role == OrgRole.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the organization owner",
        )

    await db.delete(member)
    await db.commit()

    # Revoke all refresh tokens for the removed user
    await delete_user_refresh_tokens(db, user_id)


async def update_member_role(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    role: OrgRole,
) -> dict:
    result = await db.execute(
        select(OrgMember, User)
        .join(User, User.id == OrgMember.user_id)
        .where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == user_id,
        )
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    member, user = row
    member.role = role
    await db.commit()
    await db.refresh(member)

    return {
        "user_id": user.id,
        "github_username": user.github_username,
        "name": user.name,
        "avatar_url": user.avatar_url,
        "role": member.role,
        "created_at": member.created_at,
    }

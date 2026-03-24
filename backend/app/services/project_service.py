import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import OrgMember, OrgRole
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.user import User


async def list_projects(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[Project]:
    # Check if the user is an org owner or admin — if so, show all projects
    org_result = await db.execute(
        select(OrgMember).where(
            OrgMember.org_id == org_id,
            OrgMember.user_id == user_id,
        )
    )
    org_member = org_result.scalar_one_or_none()

    if org_member is not None and org_member.role in (OrgRole.owner, OrgRole.admin):
        result = await db.execute(
            select(Project).where(Project.org_id == org_id)
        )
        return list(result.scalars().all())

    # Regular member: only projects they belong to
    result = await db.execute(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(
            Project.org_id == org_id,
            ProjectMember.user_id == user_id,
        )
    )
    return list(result.scalars().all())


async def create_project(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    description: str | None = None,
    start_date=None,
    end_date=None,
) -> Project:
    project = Project(
        org_id=org_id,
        name=name,
        description=description,
        start_date=start_date,
        end_date=end_date,
    )
    db.add(project)
    await db.flush()  # get project.id

    now = datetime.now(timezone.utc)
    lead = ProjectMember(
        project_id=project.id,
        user_id=user_id,
        role=ProjectRole.lead,
        created_at=now,
        updated_at=now,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(project)
    return project


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return project


async def update_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    **kwargs,
) -> Project:
    project = await get_project(db, project_id)
    for key, value in kwargs.items():
        if value is not None:
            setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> None:
    project = await get_project(db, project_id)
    await db.delete(project)
    await db.commit()


async def list_project_members(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> list[dict]:
    result = await db.execute(
        select(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
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


async def add_project_member(
    db: AsyncSession,
    project_id: uuid.UUID,
    github_username: str,
    role: ProjectRole,
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
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project",
        )

    now = datetime.now(timezone.utc)
    member = ProjectMember(
        project_id=project_id,
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


async def remove_project_member(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    await db.delete(member)
    await db.commit()


async def update_project_member_role(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    role: ProjectRole,
) -> dict:
    result = await db.execute(
        select(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
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

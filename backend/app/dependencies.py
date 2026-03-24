import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.organization import OrgMember, OrgRole
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.services.auth_service import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )

    token = credentials.credentials
    user_id_str = decode_access_token(token)
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired token",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token subject",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found",
        )

    return user


def require_org_role(*roles: OrgRole):
    """Returns a dependency that checks if current user has one of the given org roles.

    Expects `org_id` as a path parameter in the route.
    """

    async def check_org_role(
        org_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> OrgMember:
        result = await db.execute(
            select(OrgMember).where(
                OrgMember.org_id == org_id,
                OrgMember.user_id == current_user.id,
            )
        )
        member = result.scalar_one_or_none()

        if member is None or member.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient organization role",
            )

        return member

    return check_org_role


def require_project_role(*roles: str):
    """Returns a dependency that checks if current user has one of the given project roles,
    OR is an org owner/admin (bypass). When org admin bypasses, returns OrgMember as sentinel.

    Expects `project_id` as a path parameter in the route.
    """

    async def check_project_role(
        project_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> ProjectMember | OrgMember:
        # Look up the project to get org_id
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

        # Check if user is an org owner or admin (bypass)
        org_result = await db.execute(
            select(OrgMember).where(
                OrgMember.org_id == project.org_id,
                OrgMember.user_id == current_user.id,
            )
        )
        org_member = org_result.scalar_one_or_none()

        if org_member is not None and org_member.role in (OrgRole.owner, OrgRole.admin):
            # Return OrgMember as sentinel indicating org-level bypass
            return org_member

        # Check project-level role
        proj_result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id,
            )
        )
        proj_member = proj_result.scalar_one_or_none()

        if proj_member is None or proj_member.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient project role",
            )

        return proj_member

    return check_project_role

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_org_role, require_project_role
from app.models.organization import OrgMember, OrgRole
from app.models.project import ProjectRole
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberResponse,
    ProjectMemberUpdate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services import project_service

router = APIRouter(tags=["projects"])


@router.post(
    "/api/orgs/{org_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    org_id: uuid.UUID,
    body: ProjectCreate,
    _member: OrgMember = Depends(require_org_role(OrgRole.owner, OrgRole.admin)),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await project_service.create_project(
        db,
        org_id=org_id,
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    return project


@router.get(
    "/api/orgs/{org_id}/projects",
    response_model=list[ProjectResponse],
)
async def list_projects(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    projects = await project_service.list_projects(db, org_id=org_id, user_id=current_user.id)
    return projects


@router.get(
    "/api/projects/{project_id}",
    response_model=ProjectResponse,
)
async def get_project(
    project_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await project_service.get_project(db, project_id)
    return project


@router.patch(
    "/api/projects/{project_id}",
    response_model=ProjectResponse,
)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    _auth=Depends(require_project_role(ProjectRole.lead)),
    db: AsyncSession = Depends(get_db),
):
    project = await project_service.update_project(
        db,
        project_id,
        name=body.name,
        description=body.description,
        status=body.status,
        start_date=body.start_date,
        end_date=body.end_date,
    )
    return project


@router.delete(
    "/api/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(require_project_role(ProjectRole.lead)),
):
    await project_service.delete_project(db, project_id)


@router.get(
    "/api/projects/{project_id}/members",
    response_model=list[ProjectMemberResponse],
)
async def list_project_members(
    project_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    members = await project_service.list_project_members(db, project_id)
    return members


@router.post(
    "/api/projects/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_member(
    project_id: uuid.UUID,
    body: ProjectMemberAdd,
    _auth=Depends(require_project_role(ProjectRole.lead)),
    db: AsyncSession = Depends(get_db),
):
    member = await project_service.add_project_member(
        db, project_id, body.github_username, body.role
    )
    return member


@router.delete(
    "/api/projects/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    _auth=Depends(require_project_role(ProjectRole.lead)),
    db: AsyncSession = Depends(get_db),
):
    await project_service.remove_project_member(db, project_id, user_id)


@router.patch(
    "/api/projects/{project_id}/members/{user_id}",
    response_model=ProjectMemberResponse,
)
async def update_project_member_role(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    body: ProjectMemberUpdate,
    _auth=Depends(require_project_role(ProjectRole.lead)),
    db: AsyncSession = Depends(get_db),
):
    member = await project_service.update_project_member_role(
        db, project_id, user_id, body.role
    )
    return member

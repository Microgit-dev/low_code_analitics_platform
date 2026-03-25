from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.application.use_cases.workspace.create_workspace import CreateWorkspaceUseCase
from app.application.use_cases.workspace.delete_workspace import DeleteWorkspaceUseCase, WorkspaceNotFoundError
from app.application.use_cases.workspace.list_user_workspaces import ListUserWorkspacesUseCase
from app.application.use_cases.workspace.update_workspace import UpdateWorkspaceUseCase
from app.domain.entities.user import User
from app.infrastructure.repositories.sqlalchemy_workspace_repository import SQLAlchemyWorkspaceRepository
from app.interfaces.api.dependencies.auth import get_current_user
from app.interfaces.api.dependencies.db import get_db
from app.interfaces.api.v1.schemas.workspace import CreateWorkspaceRequest, UpdateWorkspaceRequest, WorkspaceResponse


router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkspaceResponse]:
    workspace_repo = SQLAlchemyWorkspaceRepository(db)
    use_case = ListUserWorkspacesUseCase(workspace_repo)
    workspaces = use_case.execute(current_user.id)

    return [
        WorkspaceResponse(
            id=workspace.id,
            owner_id=workspace.owner_id,
            name=workspace.name,
            description=workspace.description,
            created_at=workspace.created_at,
        )
        for workspace in workspaces
    ]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: CreateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    workspace_repo = SQLAlchemyWorkspaceRepository(db)
    use_case = CreateWorkspaceUseCase(workspace_repo)
    created_workspace = use_case.execute(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )

    return WorkspaceResponse(
        id=created_workspace.id,
        owner_id=created_workspace.owner_id,
        name=created_workspace.name,
        description=created_workspace.description,
        created_at=created_workspace.created_at,
    )


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: int,
    payload: UpdateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    workspace_repo = SQLAlchemyWorkspaceRepository(db)
    use_case = UpdateWorkspaceUseCase(workspace_repo)

    try:
        updated_workspace = use_case.execute(
            workspace_id=workspace_id,
            owner_id=current_user.id,
            name=payload.name,
            description=payload.description,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return WorkspaceResponse(
        id=updated_workspace.id,
        owner_id=updated_workspace.owner_id,
        name=updated_workspace.name,
        description=updated_workspace.description,
        created_at=updated_workspace.created_at,
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    workspace_repo = SQLAlchemyWorkspaceRepository(db)
    use_case = DeleteWorkspaceUseCase(workspace_repo)

    try:
        use_case.execute(workspace_id=workspace_id, owner_id=current_user.id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return Response(status_code=status.HTTP_204_NO_CONTENT)

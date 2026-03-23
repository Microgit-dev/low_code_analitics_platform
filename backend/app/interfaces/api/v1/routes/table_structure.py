from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.application.use_cases.workspace.manage_table_structures import (
    CreateTableRelationUseCase,
    CreateTableStructureUseCase,
    DeleteTableRelationUseCase,
    ListTableRelationsUseCase,
    ListTableStructuresUseCase,
    MoveTableColumnUseCase,
    TableRelationNotFoundError,
    TableStructureNotFoundError,
    UpdateTableStructureUseCase,
)
from app.domain.entities.user import User
from app.infrastructure.repositories.sqlalchemy_table_structure_repository import SQLAlchemyTableStructureRepository
from app.interfaces.api.dependencies.auth import get_current_user
from app.interfaces.api.dependencies.db import get_db
from app.interfaces.api.v1.schemas.table_structure import (
    MoveColumnRequest,
    RelationRequest,
    RelationResponse,
    TableStructureCreateRequest,
    TableStructureResponse,
    TableStructureUpdateRequest,
)


router = APIRouter(prefix="/workspaces/{workspace_id}/schema", tags=["Table Structures"])


@router.get("/tables", response_model=list[TableStructureResponse])
def list_table_structures(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TableStructureResponse]:
    repository = SQLAlchemyTableStructureRepository(db)
    use_case = ListTableStructuresUseCase(repository)
    structures = use_case.execute(workspace_id=workspace_id, owner_id=current_user.id)

    return [
        TableStructureResponse(
            id=item.id,
            workspace_id=item.workspace_id,
            name=item.name,
            description=item.description,
            columns=item.columns,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in structures
    ]


@router.post("/tables", response_model=TableStructureResponse, status_code=status.HTTP_201_CREATED)
def create_table_structure(
    workspace_id: int,
    payload: TableStructureCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TableStructureResponse:
    repository = SQLAlchemyTableStructureRepository(db)
    use_case = CreateTableStructureUseCase(repository)

    try:
        created = use_case.execute(
            workspace_id=workspace_id,
            owner_id=current_user.id,
            name=payload.name,
            description=payload.description,
            columns=[column.model_dump() for column in payload.columns],
        )
    except TableStructureNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return TableStructureResponse(
        id=created.id,
        workspace_id=created.workspace_id,
        name=created.name,
        description=created.description,
        columns=created.columns,
        created_at=created.created_at,
        updated_at=created.updated_at,
    )


@router.put("/tables/{table_id}", response_model=TableStructureResponse)
def update_table_structure(
    workspace_id: int,
    table_id: int,
    payload: TableStructureUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TableStructureResponse:
    repository = SQLAlchemyTableStructureRepository(db)
    use_case = UpdateTableStructureUseCase(repository)

    try:
        updated = use_case.execute(
            workspace_id=workspace_id,
            owner_id=current_user.id,
            table_id=table_id,
            name=payload.name,
            description=payload.description,
            columns=[column.model_dump() for column in payload.columns],
        )
    except TableStructureNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return TableStructureResponse(
        id=updated.id,
        workspace_id=updated.workspace_id,
        name=updated.name,
        description=updated.description,
        columns=updated.columns,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.post("/columns/move", status_code=status.HTTP_204_NO_CONTENT)
def move_column_between_tables(
    workspace_id: int,
    payload: MoveColumnRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    repository = SQLAlchemyTableStructureRepository(db)
    use_case = MoveTableColumnUseCase(repository)

    try:
        use_case.execute(
            workspace_id=workspace_id,
            owner_id=current_user.id,
            source_table_id=payload.source_table_id,
            target_table_id=payload.target_table_id,
            column_key=payload.column_key,
        )
    except TableStructureNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/relations", response_model=list[RelationResponse])
def list_table_relations(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RelationResponse]:
    repository = SQLAlchemyTableStructureRepository(db)
    use_case = ListTableRelationsUseCase(repository)
    relations = use_case.execute(workspace_id=workspace_id, owner_id=current_user.id)

    return [
        RelationResponse(
            id=item.id,
            workspace_id=item.workspace_id,
            source_table_id=item.source_table_id,
            target_table_id=item.target_table_id,
            relation_type=item.relation_type,
            name=item.name,
            mapping=item.mapping,
            properties=item.properties,
            created_at=item.created_at,
        )
        for item in relations
    ]


@router.post("/relations", response_model=RelationResponse, status_code=status.HTTP_201_CREATED)
def create_table_relation(
    workspace_id: int,
    payload: RelationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RelationResponse:
    repository = SQLAlchemyTableStructureRepository(db)
    use_case = CreateTableRelationUseCase(repository)

    try:
        created = use_case.execute(
            workspace_id=workspace_id,
            owner_id=current_user.id,
            source_table_id=payload.source_table_id,
            target_table_id=payload.target_table_id,
            relation_type=payload.relation_type,
            name=payload.name,
            mapping=payload.mapping,
            properties=payload.properties,
        )
    except TableStructureNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return RelationResponse(
        id=created.id,
        workspace_id=created.workspace_id,
        source_table_id=created.source_table_id,
        target_table_id=created.target_table_id,
        relation_type=created.relation_type,
        name=created.name,
        mapping=created.mapping,
        properties=created.properties,
        created_at=created.created_at,
    )


@router.delete("/relations/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table_relation(
    workspace_id: int,
    relation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    repository = SQLAlchemyTableStructureRepository(db)
    use_case = DeleteTableRelationUseCase(repository)

    try:
        use_case.execute(workspace_id=workspace_id, owner_id=current_user.id, relation_id=relation_id)
    except TableRelationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    return Response(status_code=status.HTTP_204_NO_CONTENT)

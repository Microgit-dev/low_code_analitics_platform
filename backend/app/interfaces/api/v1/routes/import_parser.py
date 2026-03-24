from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.services.parser_api.detectors import (
    HeaderParser,
    RowParser,
    SheetSelector,
    StructureDetector,
    TableRegionDetector,
)
from app.application.services.parser_api.models import SheetStructure
from app.application.services.parser_api.readers import TableReader
from app.domain.entities.user import User
from app.infrastructure.db.models.table_structure_model import TableStructureModel
from app.infrastructure.db.models.workspace_model import WorkspaceModel
from app.infrastructure.repositories.sqlalchemy_form_configuration_repository import (
    SQLAlchemyTableDataRecordRepository,
)
from app.infrastructure.repositories.sqlalchemy_table_structure_repository import SQLAlchemyTableStructureRepository
from app.interfaces.api.dependencies.auth import get_current_user
from app.interfaces.api.dependencies.db import get_db


router = APIRouter(prefix="/workspaces/{workspace_id}/import", tags=["Import"])


class ScanOptions(BaseModel):
    sheet_name: str | None = None
    header_row_start: int | None = None
    header_row_end: int | None = None
    data_row_start: int | None = None
    data_row_end: int | None = None
    list_split_delimiters: list[str] = Field(default_factory=lambda: [",", ";", "|", "\\n"])


class ImportTargetConfig(BaseModel):
    mode: Literal["existing", "new"]
    table_id: int | None = None
    table_name: str | None = None
    table_description: str | None = None
    column_mappings: dict[str, str | None] = Field(default_factory=dict)
    map_section_to_field: bool = False
    section_field_name: str = "Общая колонка"


class ApplyOptions(BaseModel):
    scan: ScanOptions = Field(default_factory=ScanOptions)
    targets: list[ImportTargetConfig] = Field(default_factory=list)


class ScanResponse(BaseModel):
    sheet_name: str
    source_format: str
    region: dict[str, int]
    structure: dict[str, int]
    fields: list[dict[str, Any]]
    merged_cells: list[dict[str, int]]
    artifacts: dict[str, Any]
    preview_rows: list[dict[str, Any]]
    detected_columns: list[dict[str, Any]]


class ApplyResultItem(BaseModel):
    table_id: int
    table_name: str
    created_records: int


class ApplyResponse(BaseModel):
    imported_tables: list[ApplyResultItem]


def _parse_json_form(payload: str | None, model: type[BaseModel], default: BaseModel) -> BaseModel:
    if not payload:
        return default
    try:
        return model.model_validate(json.loads(payload))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON payload: {exc}")


def _save_upload_temporarily(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "uploaded.xlsx").suffix or ".xlsx"
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = upload.file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
        tmp.write(content)
        return Path(tmp.name)


def _coerce_structure(overrides: ScanOptions, detected: SheetStructure, max_row: int) -> SheetStructure:
    header_row_start = overrides.header_row_start if overrides.header_row_start is not None else detected.header_row_start
    header_row_end = overrides.header_row_end if overrides.header_row_end is not None else detected.header_row_end
    data_row_start = overrides.data_row_start if overrides.data_row_start is not None else detected.data_row_start

    header_row_start = max(0, min(header_row_start, max_row - 1))
    header_row_end = max(header_row_start, min(header_row_end, max_row - 1))
    data_row_start = max(header_row_end + 1, min(data_row_start, max_row))

    return SheetStructure(
        header_row_start=header_row_start,
        header_row_end=header_row_end,
        numbering_row=header_row_end,
        data_row_start=data_row_start,
    )


def _infer_column_type(values: list[Any]) -> str:
    non_empty = [value for value in values if value not in (None, "")]
    if not non_empty:
        return "text"
    if any(isinstance(value, list) for value in non_empty):
        return "list"
    if all(isinstance(value, bool) for value in non_empty):
        return "boolean"
    if all(isinstance(value, (int, float)) for value in non_empty):
        return "number"
    return "text"


def _normalize_key(value: str) -> str:
    prepared = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    while "__" in prepared:
        prepared = prepared.replace("__", "_")
    normalized = prepared or "column"
    return normalized[:64]


def _build_scan_payload(file_path: Path, options: ScanOptions) -> dict[str, Any]:
    reader = TableReader()
    selector = SheetSelector()
    region_detector = TableRegionDetector()
    structure_detector = StructureDetector()
    header_parser = HeaderParser()
    row_parser = RowParser()

    sheets = selector.select(reader.read(file_path, options.sheet_name))
    if not sheets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No readable sheets found")

    sheet = sheets[0]
    region = region_detector.detect(sheet)
    detected_structure = structure_detector.detect(sheet, region)
    structure = _coerce_structure(options, detected_structure, sheet.nrows)

    fields = header_parser.build_fields(sheet, structure, region)
    sections, rows = row_parser.parse_rows(sheet, region, structure, fields)

    if options.data_row_end is not None:
        max_rows = max(0, options.data_row_end - structure.data_row_start + 1)
        rows = rows[:max_rows]

    merged_cells = [
        {
            "row_start": row_start,
            "row_end": row_end,
            "col_start": col_start,
            "col_end": col_end,
        }
        for row_start, row_end, col_start, col_end in sheet.merged_cells
    ]

    field_keys = [field.key for field in fields]
    if any("Общая колонка" in row for row in rows) and "Общая колонка" not in field_keys:
        field_keys.insert(0, "Общая колонка")

    detected_columns: list[dict[str, Any]] = []
    for key in field_keys:
        sample_values = [row.get(key) for row in rows[:100]]
        detected_type = _infer_column_type(sample_values)
        settings: dict[str, Any] = {}
        if detected_type == "list":
            settings = {
                "itemType": "text",
                "splitDelimiters": options.list_split_delimiters,
            }
        detected_columns.append(
            {
                "source_key": key,
                "suggested_key": _normalize_key(key),
                "suggested_name": key,
                "suggested_type": detected_type,
                "settings": settings,
            }
        )

    return {
        "sheet_name": sheet.name,
        "source_format": sheet.source_format,
        "region": asdict(region),
        "structure": asdict(structure),
        "fields": [
            {
                "key": field.key,
                "path": list(field.path),
                "columns": list(field.columns),
                "is_multi_value": field.is_multi_value,
            }
            for field in fields
        ],
        "merged_cells": merged_cells,
        "artifacts": {
            "merged_cells_count": len(merged_cells),
            "sections_count": len(sections),
            "detected_sections": [section.value for section in sections[:50]],
        },
        "preview_rows": rows[:200],
        "rows": rows,
        "detected_columns": detected_columns,
    }


def _ensure_workspace_owner(db: Session, workspace_id: int, owner_id: int) -> None:
    workspace = (
        db.query(WorkspaceModel)
        .filter(WorkspaceModel.id == workspace_id, WorkspaceModel.owner_id == owner_id)
        .first()
    )
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")


def _convert_value_for_column(value: Any, target_column: dict[str, Any], delimiters: list[str]) -> Any:
    if value in (None, ""):
        return None

    col_type = target_column.get("type")
    if col_type == "list":
        if isinstance(value, list):
            return [item for item in value if item not in (None, "")]
        if isinstance(value, str):
            tokens = [value]
            for delimiter in delimiters:
                expanded: list[str] = []
                for token in tokens:
                    expanded.extend(token.split(delimiter))
                tokens = expanded
            return [token.strip() for token in tokens if token.strip()]
        return [value]

    if col_type == "number":
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                return None

    if col_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "да"}:
                return True
            if lowered in {"false", "0", "no", "нет"}:
                return False

    return value


@router.post("/scan", response_model=ScanResponse)
def scan_import_file(
    workspace_id: int,
    file: UploadFile = File(...),
    options_json: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanResponse:
    _ensure_workspace_owner(db, workspace_id, current_user.id)

    options = _parse_json_form(options_json, ScanOptions, ScanOptions())
    temp_path = _save_upload_temporarily(file)

    try:
        payload = _build_scan_payload(temp_path, options)
        return ScanResponse(
            sheet_name=payload["sheet_name"],
            source_format=payload["source_format"],
            region=payload["region"],
            structure=payload["structure"],
            fields=payload["fields"],
            merged_cells=payload["merged_cells"],
            artifacts=payload["artifacts"],
            preview_rows=payload["preview_rows"],
            detected_columns=payload["detected_columns"],
        )
    finally:
        temp_path.unlink(missing_ok=True)


@router.post("/apply", response_model=ApplyResponse)
def apply_import_file(
    workspace_id: int,
    file: UploadFile = File(...),
    config_json: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplyResponse:
    _ensure_workspace_owner(db, workspace_id, current_user.id)

    config = _parse_json_form(config_json, ApplyOptions, ApplyOptions())
    if not config.targets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No targets selected")

    temp_path = _save_upload_temporarily(file)
    try:
        scan_payload = _build_scan_payload(temp_path, config.scan)
        rows: list[dict[str, Any]] = scan_payload["rows"]
        if not rows:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No parsed rows found")

        table_repo = SQLAlchemyTableStructureRepository(db)
        data_repo = SQLAlchemyTableDataRecordRepository(db)
        imported_tables: list[ApplyResultItem] = []

        for target in config.targets:
            if target.mode == "existing":
                if target.table_id is None:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="existing target requires table_id")
                table_model = (
                    db.query(TableStructureModel)
                    .join(WorkspaceModel, WorkspaceModel.id == TableStructureModel.workspace_id)
                    .filter(
                        TableStructureModel.id == target.table_id,
                        TableStructureModel.workspace_id == workspace_id,
                        WorkspaceModel.owner_id == current_user.id,
                    )
                    .first()
                )
                if table_model is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Table {target.table_id} not found")

                if target.map_section_to_field:
                    section_key = _normalize_key(target.section_field_name or "section")
                    current_columns = list(table_model.columns_json or [])
                    has_section_column = any(
                        isinstance(column, dict) and column.get("key") == section_key
                        for column in current_columns
                    )
                    if not has_section_column:
                        current_columns.append(
                            {
                                "key": section_key,
                                "name": target.section_field_name or "Разделитель",
                                "type": "text",
                                "required": False,
                                "settings": {
                                    "source": "import_separator",
                                },
                            }
                        )
                        table_model.columns_json = current_columns
                        db.add(table_model)
                        db.commit()
                        db.refresh(table_model)

                target_table_id = table_model.id
                target_table_name = table_model.name
                target_columns = {col.get("key"): col for col in (table_model.columns_json or []) if isinstance(col, dict)}
            else:
                if not target.table_name:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="new target requires table_name")

                new_columns: list[dict[str, Any]] = []
                for detected in scan_payload["detected_columns"]:
                    source_key = detected["source_key"]
                    mapped = target.column_mappings.get(source_key)
                    if not mapped:
                        continue
                    safe_mapped = _normalize_key(mapped)
                    col_type = detected["suggested_type"]
                    if col_type not in {"text", "number", "boolean", "date", "datetime", "enum", "list", "geoPoint", "geoPolygon"}:
                        col_type = "text"
                    new_columns.append(
                        {
                            "key": safe_mapped,
                            "name": detected["suggested_name"],
                            "type": col_type,
                            "required": False,
                            "settings": detected.get("settings", {}),
                        }
                    )

                if target.map_section_to_field:
                    section_key = _normalize_key(target.section_field_name or "section")
                    if all(column.get("key") != section_key for column in new_columns):
                        new_columns.append(
                            {
                                "key": section_key,
                                "name": target.section_field_name or "Общая колонка",
                                "type": "text",
                                "required": False,
                                "settings": {},
                            }
                        )

                created = table_repo.create_table(
                    workspace_id=workspace_id,
                    owner_id=current_user.id,
                    name=target.table_name,
                    description=target.table_description,
                    columns=new_columns,
                )
                if created is None:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create target table")
                target_table_id = created.id
                target_table_name = created.name
                target_columns = {col.get("key"): col for col in (created.columns or []) if isinstance(col, dict)}

            created_count = 0
            delimiters = config.scan.list_split_delimiters or [",", ";", "|", "\\n"]
            for row in rows:
                payload: dict[str, Any] = {}
                for source_key, target_key in target.column_mappings.items():
                    if not target_key:
                        continue
                    target_column = target_columns.get(target_key)
                    if target_column is None:
                        continue
                    payload[target_key] = _convert_value_for_column(
                        row.get(source_key),
                        target_column,
                        delimiters,
                    )

                if target.map_section_to_field and "Общая колонка" in row:
                    section_key = _normalize_key(target.section_field_name or "section")
                    payload[section_key] = row.get("Общая колонка")

                if not any(value not in (None, "", []) for value in payload.values()):
                    continue

                data_repo.create_from_form(
                    workspace_id=workspace_id,
                    table_id=target_table_id,
                    data=payload,
                    submitter_email=None,
                )
                created_count += 1

            imported_tables.append(
                ApplyResultItem(
                    table_id=target_table_id,
                    table_name=target_table_name,
                    created_records=created_count,
                )
            )

        return ApplyResponse(imported_tables=imported_tables)
    finally:
        temp_path.unlink(missing_ok=True)

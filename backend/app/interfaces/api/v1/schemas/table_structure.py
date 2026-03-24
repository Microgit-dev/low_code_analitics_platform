from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ColumnType = Literal[
    "text",
    "number",
    "boolean",
    "date",
    "datetime",
    "enum",
    "list",
    "geoPoint",
    "geoPolygon",
]

RelationType = Literal["one_to_one", "one_to_many", "many_to_many"]


class ColumnDefinition(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    type: ColumnType
    required: bool = False
    settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_settings(self) -> "ColumnDefinition":
        if self.type == "number":
            auto_increment = self.settings.get("autoIncrement", False)
            is_id = self.settings.get("isId", False)

            if not isinstance(auto_increment, bool):
                raise ValueError("number type settings.autoIncrement must be boolean")
            if not isinstance(is_id, bool):
                raise ValueError("number type settings.isId must be boolean")

            if is_id and not auto_increment:
                raise ValueError("number id column requires settings.autoIncrement=true")

            start = self.settings.get("autoIncrementStart", 1)
            step = self.settings.get("autoIncrementStep", 1)
            if not isinstance(start, int):
                raise ValueError("number autoIncrementStart must be integer")
            if not isinstance(step, int) or step <= 0:
                raise ValueError("number autoIncrementStep must be positive integer")

        if self.type == "enum":
            options = self.settings.get("options")
            if not isinstance(options, list) or not options or not all(isinstance(item, str) and item for item in options):
                raise ValueError("enum type requires settings.options as non-empty string list")

        if self.type == "list":
            item_type = self.settings.get("itemType")
            if item_type not in ["text", "number", "boolean", "enum"]:
                raise ValueError("list type requires settings.itemType in [text, number, boolean, enum]")
            if item_type == "enum":
                options = self.settings.get("options")
                if not isinstance(options, list) or not options:
                    raise ValueError("list enum type requires settings.options")

        if self.type in ["geoPoint", "geoPolygon"]:
            srid = self.settings.get("srid", 4326)
            if not isinstance(srid, int) or srid <= 0:
                raise ValueError("geo types require positive integer settings.srid")

        return self


class TableStructureCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    columns: list[ColumnDefinition] = Field(default_factory=list)


class TableStructureUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    columns: list[ColumnDefinition] = Field(default_factory=list)


class TableStructureResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    description: str | None
    columns: list[ColumnDefinition]
    created_at: datetime
    updated_at: datetime


class MoveColumnRequest(BaseModel):
    source_table_id: int
    target_table_id: int
    column_key: str = Field(min_length=1, max_length=64)


class RelationRequest(BaseModel):
    source_table_id: int
    target_table_id: int
    relation_type: RelationType
    name: str = Field(min_length=2, max_length=255)
    mapping: dict[str, str] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)


class RelationResponse(BaseModel):
    id: int
    workspace_id: int
    source_table_id: int
    target_table_id: int
    relation_type: RelationType
    name: str
    mapping: dict[str, str]
    properties: dict[str, Any]
    created_at: datetime

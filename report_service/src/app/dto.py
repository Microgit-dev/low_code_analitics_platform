from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy.engine import URL


class ColumnSchema(BaseModel):
    name: str
    type: str


class TableSchema(BaseModel):
    name: str
    columns: List[ColumnSchema]


class Relation(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class DbSchema(BaseModel):
    tables: List[TableSchema] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)

    def table_names(self) -> List[str]:
        return [t.name for t in self.tables]

    def columns_by_table(self) -> Dict[str, List[str]]:
        return {t.name: [c.name for c in t.columns] for t in self.tables}


class FunctionCatalogItem(BaseModel):
    name: str
    description: str
    example: str


class DbConnection(BaseModel):
    driver: str = Field(default="postgresql+psycopg")
    host: str
    port: int = 5432
    user: str
    password: str
    database: str
    sslmode: Optional[str] = None

    def sqlalchemy_url(self) -> str:
        query: Dict[str, str] = {}
        if self.sslmode:
            query["sslmode"] = self.sslmode

        return URL.create(
            drivername=self.driver,
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
            query=query,
        ).render_as_string(hide_password=False)

    def sqlalchemy_connect_args(self) -> Dict[str, str]:
        return {
            "options": "-c default_transaction_read_only=on",
        }


class ReportGenerationRequest(BaseModel):
    template_html: str
    report_request: str
    db_schema: DbSchema
    function_catalog: List[FunctionCatalogItem] = Field(default_factory=list)
    db: DbConnection
    debug: bool = False


class ReportGenerationResponse(BaseModel):
    sql: str
    rows: List[Dict[str, Any]]
    html: str
    debug_info: Optional[Dict[str, Any]] = None

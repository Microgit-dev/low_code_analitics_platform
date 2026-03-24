from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import ParsedDocument
from .service import ParsingService


class ParsedWorkbook:
    def __init__(self, document: ParsedDocument) -> None:
        self.document = document
        self.sheet = document.primary_sheet()
        self.sheet_name = self.sheet.name
        self.fields = self.sheet.fields
        self.rows = self.sheet.to_csv_rows()

    def to_csv_rows(self) -> list[dict[str, Any]]:
        return self.rows


class UniversalXlsParser:
    def __init__(self) -> None:
        self.service = ParsingService()

    def parse(self, path: str | Path, sheet_name: str | None = None) -> ParsedWorkbook:
        document = self.service.parse(path, sheet_name=sheet_name)
        return ParsedWorkbook(document)

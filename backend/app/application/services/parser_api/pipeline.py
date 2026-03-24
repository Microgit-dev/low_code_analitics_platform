from __future__ import annotations

from pathlib import Path

from .models import ParsedDocument
from .service import ParsingService


class UniversalSpreadsheetParser:
    def __init__(self) -> None:
        self.service = ParsingService()

    def parse(self, path: str | Path, sheet_name: str | None = None) -> ParsedDocument:
        return self.service.parse(path, sheet_name=sheet_name)

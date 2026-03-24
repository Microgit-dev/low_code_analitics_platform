from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TableSheet:
    name: str
    nrows: int
    ncols: int
    merged_cells: tuple[tuple[int, int, int, int], ...]
    cells: tuple[tuple[Any, ...], ...]
    source_format: str

    def cell_value(self, row_index: int, column_index: int) -> Any:
        if row_index >= self.nrows or column_index >= self.ncols:
            return None
        return self.cells[row_index][column_index]


@dataclass(frozen=True)
class TableRegion:
    row_start: int
    row_end: int
    col_start: int
    col_end: int


@dataclass(frozen=True)
class HeaderField:
    key: str
    path: tuple[str, ...]
    columns: tuple[int, ...]

    @property
    def is_multi_value(self) -> bool:
        return len(self.columns) > 1


@dataclass(frozen=True)
class SheetStructure:
    header_row_start: int
    header_row_end: int
    numbering_row: int
    data_row_start: int


@dataclass(frozen=True)
class SectionContext:
    value: str


@dataclass(frozen=True)
class ParsedRow:
    row_index: int
    context: SectionContext | None
    values: dict[str, Any]

    def to_flat_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.context:
            payload["Общая колонка"] = self.context.value
        payload.update(self.values)
        return payload


@dataclass(frozen=True)
class ParsedSheet:
    name: str
    structure: SheetStructure
    fields: list[HeaderField]
    sections: list[SectionContext]
    rows: list[ParsedRow]

    def to_csv_rows(self, *, list_delimiter: str = ", ") -> list[dict[str, Any]]:
        csv_rows: list[dict[str, Any]] = []
        for row in self.rows:
            base = row.to_flat_dict()
            for key, value in base.items():
                if isinstance(value, list):
                    base[key] = list_delimiter.join(
                        "" if item is None else str(item) for item in value
                    )
            csv_rows.append(base)
        return csv_rows


@dataclass(frozen=True)
class ParsedDocument:
    source_path: str
    sheets: list[ParsedSheet]

    def primary_sheet(self) -> ParsedSheet:
        return max(self.sheets, key=lambda sheet: len(sheet.rows))

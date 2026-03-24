from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .models import HeaderField, SectionContext, SheetStructure, TableRegion, TableSheet


MULTISPACE_RE = re.compile(r"\s+")


class SheetSelector:
    def select(self, sheets: list[TableSheet]) -> list[TableSheet]:
        return [sheet for sheet in sheets if sheet.nrows and sheet.ncols]


class TableRegionDetector:
    def detect(self, sheet: TableSheet) -> TableRegion:
        non_empty_rows = [row for row in range(sheet.nrows) if self._row_has_content(sheet, row)]
        non_empty_cols = [col for col in range(sheet.ncols) if self._col_has_content(sheet, col)]
        if not non_empty_rows or not non_empty_cols:
            return TableRegion(0, sheet.nrows, 0, sheet.ncols)
        return TableRegion(
            row_start=min(non_empty_rows),
            row_end=max(non_empty_rows) + 1,
            col_start=min(non_empty_cols),
            col_end=max(non_empty_cols) + 1,
        )

    def _row_has_content(self, sheet: TableSheet, row_index: int) -> bool:
        return any(sheet.cell_value(row_index, col) not in ("", None) for col in range(sheet.ncols))

    def _col_has_content(self, sheet: TableSheet, column_index: int) -> bool:
        return any(sheet.cell_value(row, column_index) not in ("", None) for row in range(sheet.nrows))


class StructureDetector:
    MIN_NUMBERING_SCORE = 20

    def __init__(self, *, header_scan_limit: int = 50) -> None:
        self.header_scan_limit = header_scan_limit

    def detect(self, sheet: TableSheet, region: TableRegion) -> SheetStructure:
        if sheet.source_format == "csv":
            return SheetStructure(
                header_row_start=region.row_start,
                header_row_end=region.row_start,
                numbering_row=region.row_start,
                data_row_start=region.row_start + 1,
            )

        numbering_row = self._find_numbering_row(sheet, region)
        header_row_end = max(numbering_row - 1, region.row_start)
        header_row_start = self._find_header_start(sheet, region, numbering_row)
        return SheetStructure(
            header_row_start=header_row_start,
            header_row_end=header_row_end,
            numbering_row=numbering_row,
            data_row_start=numbering_row + 1,
        )

    def _find_numbering_row(self, sheet: TableSheet, region: TableRegion) -> int:
        best_row_index = region.row_start
        best_score = -1
        upper_bound = min(region.row_end, region.row_start + self.header_scan_limit)
        for row_index in range(region.row_start, upper_bound):
            numbers: list[int] = []
            for column_index in range(region.col_start, region.col_end):
                number = self._as_integer(sheet.cell_value(row_index, column_index))
                if number is not None:
                    numbers.append(number)
            if len(numbers) < 3:
                continue
            ascending_pairs = sum(1 for left, right in zip(numbers, numbers[1:]) if right == left + 1)
            score = ascending_pairs * 10 + len(numbers) + (20 if numbers[0] == 1 else 0)
            if score > best_score:
                best_row_index = row_index
                best_score = score
        if best_score >= self.MIN_NUMBERING_SCORE:
            return best_row_index
        return self._find_best_text_header_row(sheet, region)

    def _find_best_text_header_row(self, sheet: TableSheet, region: TableRegion) -> int:
        for row_index in range(region.row_start, min(region.row_end, region.row_start + self.header_scan_limit)):
            non_empty_text = 0
            for column_index in range(region.col_start, region.col_end):
                value = sheet.cell_value(row_index, column_index)
                if isinstance(value, str) and self._normalize_text(value):
                    non_empty_text += 1
            if non_empty_text >= max(2, (region.col_end - region.col_start) // 3):
                return row_index
        return region.row_start

    def _find_header_start(self, sheet: TableSheet, region: TableRegion, numbering_row: int) -> int:
        merged_header_starts = [
            row_start
            for row_start, row_end, col_start, col_end in sheet.merged_cells
            if row_start < numbering_row <= row_end and col_start < region.col_end and col_end > region.col_start
        ]
        if merged_header_starts:
            return max(region.row_start, min(merged_header_starts))
        for row_index in range(numbering_row - 1, region.row_start - 1, -1):
            if self._row_has_text(sheet, row_index, region):
                return row_index
        return region.row_start

    def _row_has_text(self, sheet: TableSheet, row_index: int, region: TableRegion) -> bool:
        for column_index in range(region.col_start, region.col_end):
            value = sheet.cell_value(row_index, column_index)
            if isinstance(value, str) and self._normalize_text(value):
                return True
        return False

    def _normalize_text(self, value: str) -> str:
        value = value.replace("\n", " ").replace("\xa0", " ")
        return MULTISPACE_RE.sub(" ", value).strip(" .")

    def _as_integer(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str) and re.fullmatch(r"\d+", value.strip()):
            return int(value.strip())
        return None


class HeaderParser:
    def build_fields(self, sheet: TableSheet, structure: SheetStructure, region: TableRegion) -> list[HeaderField]:
        if sheet.source_format == "csv":
            return self._build_csv_fields(sheet, structure, region)

        header_paths: list[tuple[str, ...]] = []
        for column_index in range(region.col_start, region.col_end):
            labels: list[str] = []
            for row_index in range(structure.header_row_start, structure.header_row_end + 1):
                label = self._covered_text(sheet, row_index, column_index)
                normalized = self._normalize_header_text(label)
                if normalized and normalized not in labels:
                    labels.append(normalized)
            header_paths.append(tuple(labels))
        return self._collapse_paths(header_paths, region.col_start)

    def _build_csv_fields(self, sheet: TableSheet, structure: SheetStructure, region: TableRegion) -> list[HeaderField]:
        fields: list[HeaderField] = []
        for column_index in range(region.col_start, region.col_end):
            raw = sheet.cell_value(structure.header_row_start, column_index)
            header = self._normalize_header_text(self._stringify(raw)) or f"Колонка_{column_index + 1}"
            fields.append(HeaderField(key=header, path=(header,), columns=(column_index,)))
        return fields

    def _collapse_paths(self, header_paths: list[tuple[str, ...]], column_offset: int) -> list[HeaderField]:
        fields: list[HeaderField] = []
        current_path: tuple[str, ...] | None = None
        current_columns: list[int] = []
        for local_index, path in enumerate(header_paths):
            if not path:
                continue
            column_index = column_offset + local_index
            if path == current_path:
                current_columns.append(column_index)
                continue
            if current_path is not None:
                fields.append(HeaderField(key="_".join(current_path), path=current_path, columns=tuple(current_columns)))
            current_path = path
            current_columns = [column_index]
        if current_path is not None:
            fields.append(HeaderField(key="_".join(current_path), path=current_path, columns=tuple(current_columns)))
        return fields

    def _covered_text(self, sheet: TableSheet, row_index: int, column_index: int) -> str:
        for row_start, row_end, col_start, col_end in sheet.merged_cells:
            if row_start <= row_index < row_end and col_start <= column_index < col_end:
                return self._stringify(sheet.cell_value(row_start, col_start))
        return self._stringify(sheet.cell_value(row_index, column_index))

    def _normalize_header_text(self, value: str) -> str:
        value = self._normalize_text(value)
        if not value or re.fullmatch(r"\d+", value):
            return ""
        return value

    def _normalize_text(self, value: str) -> str:
        value = value.replace("\n", " ").replace("\xa0", " ")
        return MULTISPACE_RE.sub(" ", value).strip(" .")

    def _stringify(self, value: Any) -> str:
        if value in ("", None):
            return ""
        if isinstance(value, datetime):
            return value.isoformat(sep=" ", timespec="minutes")
        return str(value).strip()


class RowParser:
    def __init__(self, *, dash_as_none: bool = True) -> None:
        self.dash_as_none = dash_as_none

    def parse_rows(
        self,
        sheet: TableSheet,
        region: TableRegion,
        structure: SheetStructure,
        fields: list[HeaderField],
    ) -> tuple[list[SectionContext], list[dict[str, Any]]]:
        if sheet.source_format == "csv":
            return [], self._parse_csv_rows(sheet, region, structure, fields)

        sections: list[SectionContext] = []
        rows: list[dict[str, Any]] = []
        current_context: SectionContext | None = None
        for row_index in range(structure.data_row_start, region.row_end):
            if self._is_context_row(sheet, row_index, region):
                current_context = SectionContext(value=self._normalize_text(self._stringify(sheet.cell_value(row_index, region.col_start))))
                sections.append(current_context)
                continue
            if not self._is_data_row(sheet, row_index, region):
                continue
            row = {}
            if current_context:
                row["Общая колонка"] = current_context.value
            for field in fields:
                values = [self._normalize_cell_value(sheet.cell_value(row_index, col)) for col in field.columns]
                row[field.key] = values if field.is_multi_value else values[0]
            rows.append(row)
        return sections, rows

    def _parse_csv_rows(
        self,
        sheet: TableSheet,
        region: TableRegion,
        structure: SheetStructure,
        fields: list[HeaderField],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row_index in range(structure.data_row_start, region.row_end):
            row: dict[str, Any] = {}
            is_empty = True
            for field in fields:
                value = self._normalize_cell_value(sheet.cell_value(row_index, field.columns[0]))
                row[field.key] = value
                if value not in ("", None):
                    is_empty = False
            if not is_empty:
                rows.append(row)
        return rows

    def _is_context_row(self, sheet: TableSheet, row_index: int, region: TableRegion) -> bool:
        for row_start, row_end, col_start, col_end in sheet.merged_cells:
            if row_start == row_index and col_start <= region.col_start and col_end >= region.col_end:
                return bool(self._stringify(sheet.cell_value(row_index, region.col_start)))
        first_value = self._normalize_text(self._stringify(sheet.cell_value(row_index, region.col_start)))
        if not first_value:
            return False
        remaining = [
            sheet.cell_value(row_index, column_index)
            for column_index in range(region.col_start + 1, region.col_end)
        ]
        return all(value in ("", None) for value in remaining)

    def _is_data_row(self, sheet: TableSheet, row_index: int, region: TableRegion) -> bool:
        values = [
            self._normalize_cell_value(sheet.cell_value(row_index, column_index))
            for column_index in range(region.col_start, region.col_end)
        ]
        return any(value not in ("", None, []) for value in values)

    def _normalize_cell_value(self, value: Any) -> Any:
        if value in ("", None):
            return None
        if isinstance(value, str):
            text = self._normalize_text(value)
            if self.dash_as_none and text == "-":
                return None
            return text
        if isinstance(value, datetime):
            return value.isoformat(sep=" ", timespec="minutes")
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value) if value.is_integer() else float(value)
        return value

    def _normalize_text(self, value: str) -> str:
        value = value.replace("\n", " ").replace("\xa0", " ")
        return MULTISPACE_RE.sub(" ", value).strip(" .")

    def _stringify(self, value: Any) -> str:
        if value in ("", None):
            return ""
        if isinstance(value, datetime):
            return value.isoformat(sep=" ", timespec="minutes")
        return str(value).strip()

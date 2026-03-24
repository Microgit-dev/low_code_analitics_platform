from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


class CsvWriter:
    def write(
        self,
        rows: list[dict[str, Any]],
        output_path: str | Path,
        *,
        delimiter: str = ";",
        list_delimiter: str = ", ",
    ) -> Path:
        normalized_rows = [self._normalize_row(row, list_delimiter=list_delimiter) for row in rows]
        output_path = Path(output_path)
        with output_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(normalized_rows[0].keys()) if normalized_rows else [],
                delimiter=delimiter,
            )
            if normalized_rows:
                writer.writeheader()
                writer.writerows(normalized_rows)
        return output_path

    def _normalize_row(self, row: dict[str, Any], *, list_delimiter: str) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, list):
                cleaned_items = [str(item) for item in value if item not in (None, "")]
                if not cleaned_items:
                    normalized[key] = ""
                else:
                    normalized[key] = list_delimiter.join(cleaned_items)
            else:
                normalized[key] = value
        return normalized

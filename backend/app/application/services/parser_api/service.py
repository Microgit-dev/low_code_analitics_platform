from __future__ import annotations

from pathlib import Path
import re

from .detectors import HeaderParser, RowParser, SheetSelector, StructureDetector, TableRegionDetector
from .models import ParsedDocument, ParsedRow, ParsedSheet
from .readers import TableReader
from .serializers import CsvWriter


class ParsingService:
    def __init__(self) -> None:
        self.reader = TableReader()
        self.sheet_selector = SheetSelector()
        self.region_detector = TableRegionDetector()
        self.structure_detector = StructureDetector()
        self.header_parser = HeaderParser()
        self.row_parser = RowParser()
        self.csv_writer = CsvWriter()

    def parse(self, path: str | Path, sheet_name: str | None = None) -> ParsedDocument:
        source_path = str(path)
        sheets = self.sheet_selector.select(self.reader.read(path, sheet_name))
        parsed_sheets: list[ParsedSheet] = []
        for sheet in sheets:
            region = self.region_detector.detect(sheet)
            structure = self.structure_detector.detect(sheet, region)
            fields = self.header_parser.build_fields(sheet, structure, region)
            sections, row_values = self.row_parser.parse_rows(sheet, region, structure, fields)
            rows = [ParsedRow(row_index=index, context=None, values=row) for index, row in enumerate(row_values)]
            parsed_sheets.append(
                ParsedSheet(
                    name=sheet.name,
                    structure=structure,
                    fields=fields,
                    sections=sections,
                    rows=rows,
                )
            )
        return ParsedDocument(source_path=source_path, sheets=parsed_sheets)

    def convert_to_csv(
        self,
        input_path: str | Path,
        output_path: str | Path,
        *,
        sheet_name: str | None = None,
        delimiter: str = ";",
        list_delimiter: str = ", ",
    ) -> Path:
        document = self.parse(input_path, sheet_name=sheet_name)
        sheet = document.primary_sheet()
        rows = [row.to_flat_dict() for row in sheet.rows]
        return self.csv_writer.write(
            rows,
            output_path,
            delimiter=delimiter,
            list_delimiter=list_delimiter,
        )

    def convert_all_to_csv(
        self,
        input_path: str | Path,
        output_dir: str | Path,
        *,
        delimiter: str = ";",
        list_delimiter: str = ", ",
    ) -> list[Path]:
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        document = self.parse(input_path)
        if not document.sheets:
            return []

        if len(document.sheets) == 1:
            single_output = output_dir / f"{input_path.stem}.csv"
            return [
                self.convert_to_csv(
                    input_path,
                    single_output,
                    delimiter=delimiter,
                    list_delimiter=list_delimiter,
                )
            ]

        written_paths: list[Path] = []
        for sheet in document.sheets:
            safe_sheet_name = self._sanitize_filename(sheet.name)
            output_path = output_dir / f"{input_path.stem}__{safe_sheet_name}.csv"
            rows = [row.to_flat_dict() for row in sheet.rows]
            written_paths.append(
                self.csv_writer.write(
                    rows,
                    output_path,
                    delimiter=delimiter,
                    list_delimiter=list_delimiter,
                )
            )
        return written_paths

    def _sanitize_filename(self, value: str) -> str:
        value = re.sub(r'[\\\\/:*?\"<>|]+', "_", value.strip())
        value = re.sub(r"\s+", " ", value).strip()
        return value or "sheet"

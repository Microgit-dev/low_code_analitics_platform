from __future__ import annotations

import argparse
from pathlib import Path

from .service import ParsingService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Universal parser for table files.")
    parser.add_argument("input", help="Path to .xls/.xlsx/.csv file")
    parser.add_argument("--output", help="Optional output directory or explicit .csv file path")
    parser.add_argument(
        "--list-delimiter",
        default=", ",
        help="Delimiter for nested list values inside a single CSV cell",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    service = ParsingService()
    input_path = Path(args.input)
    if args.output and args.output.lower().endswith(".csv"):
        service.convert_to_csv(
            args.input,
            Path(args.output),
            delimiter=";",
            list_delimiter=args.list_delimiter,
        )
        return

    output_dir = Path(args.output) if args.output else Path.cwd()
    service.convert_all_to_csv(
        args.input,
        output_dir,
        delimiter=";",
        list_delimiter=args.list_delimiter,
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import html
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}


def wtag(name: str) -> str:
    return f"{{{W_NS}}}{name}"


@dataclass
class Cell:
    col: int
    colspan: int = 1
    rowspan: int = 1
    text_html: str = ""
    style: Dict[str, str] = field(default_factory=dict)


@dataclass
class Row:
    cells: List[Cell] = field(default_factory=list)


@dataclass
class Table:
    rows: List[Row]
    col_widths_twips: List[int]


def twips_to_px(twips: Optional[int]) -> Optional[float]:
    if twips is None:
        return None
    return round(twips / 15.0, 2)


def twips_to_pct(values: List[int]) -> List[float]:
    total = sum(v for v in values if v)
    if not total:
        return []
    return [round(v * 100.0 / total, 2) for v in values]


def xml_text(el: etree._Element, path: str) -> Optional[str]:
    node = el.find(path, namespaces=NS)
    if node is None:
        return None
    return node.get(wtag("val"))


def normalize_whitespace(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def preserve_xml_spaces(text: str) -> str:
    if not text:
        return ""
    escaped = html.escape(text)
    escaped = escaped.replace("\t", "&emsp;")
    escaped = escaped.replace("\n", "<br>")
    # preserve repeated / leading / trailing spaces in HTML
    escaped = re.sub(r" {2,}", lambda m: "&nbsp;" * len(m.group(0)), escaped)
    escaped = re.sub(r"^ +", lambda m: "&nbsp;" * len(m.group(0)), escaped)
    escaped = re.sub(r" +$", lambda m: "&nbsp;" * len(m.group(0)), escaped)
    return escaped


def border_to_css(border_el: Optional[etree._Element]) -> Optional[str]:
    if border_el is None:
        return None
    val = border_el.get(wtag("val"))
    if val in {None, "nil", "none"}:
        return "none"
    color = border_el.get(wtag("color"), "000000")
    if color == "auto":
        color = "000000"
    sz = border_el.get(wtag("sz"))
    px = 1
    if sz:
        try:
            # OOXML border size is in eighths of a point.
            pt = int(sz) / 8.0
            px = max(1, round(pt * 96 / 72))
        except ValueError:
            px = 1
    style_map = {
        "single": "solid",
        "dashed": "dashed",
        "dotted": "dotted",
        "double": "double",
    }
    css_style = style_map.get(val, "solid")
    return f"{px}px {css_style} #{color}"


def parse_run(run: etree._Element) -> str:
    parts: List[str] = []
    for child in run:
        if child.tag == wtag("t"):
            parts.append(preserve_xml_spaces(child.text or ""))
        elif child.tag == wtag("tab"):
            parts.append('<span class="docx-tab"></span>')
        elif child.tag in {wtag("br"), wtag("cr")}:
            parts.append("<br>")
    text = "".join(parts)
    if not text:
        return ""

    rpr = run.find("./w:rPr", namespaces=NS)
    if rpr is not None:
        if rpr.find("./w:b", namespaces=NS) is not None:
            text = f"<strong>{text}</strong>"
        if rpr.find("./w:i", namespaces=NS) is not None:
            text = f"<em>{text}</em>"
        if rpr.find("./w:u", namespaces=NS) is not None:
            text = f"<span style=\"text-decoration: underline;\">{text}</span>"
    return text


ALIGN_MAP = {
    "left": "left",
    "center": "center",
    "right": "right",
    "both": "justify",
    "justify": "justify",
}


VALIGN_MAP = {
    "top": "top",
    "center": "middle",
    "bottom": "bottom",
}



def parse_paragraph(par: etree._Element) -> str:
    pieces: List[str] = []
    for child in par:
        if child.tag == wtag("r"):
            pieces.append(parse_run(child))
        elif child.tag == wtag("hyperlink"):
            for r in child.findall("./w:r", namespaces=NS):
                pieces.append(parse_run(r))
    content = "".join(pieces)
    if not content:
        return ""

    ppr = par.find("./w:pPr", namespaces=NS)
    styles: List[str] = []
    if ppr is not None:
        jc = ppr.find("./w:jc", namespaces=NS)
        if jc is not None:
            align = ALIGN_MAP.get(jc.get(wtag("val"), "left"), "left")
            styles.append(f"text-align:{align}")
    if styles:
        return f'<div style="{";".join(styles)}">{content}</div>'
    return content



def parse_cell_text(tc: etree._Element) -> str:
    paragraphs = [parse_paragraph(p) for p in tc.findall("./w:p", namespaces=NS)]
    paragraphs = [p for p in paragraphs if p]
    if not paragraphs:
        return "&nbsp;"
    return "<br>".join(paragraphs)



def parse_cell_style(tc: etree._Element) -> Dict[str, str]:
    tcpr = tc.find("./w:tcPr", namespaces=NS)
    style: Dict[str, str] = {
        "vertical-align": "middle",
        "padding": "4px 5px",
    }
    if tcpr is None:
        return style

    v_align = tcpr.find("./w:vAlign", namespaces=NS)
    if v_align is not None:
        style["vertical-align"] = VALIGN_MAP.get(v_align.get(wtag("val"), "center"), "middle")

    tc_mar = tcpr.find("./w:tcMar", namespaces=NS)
    if tc_mar is not None:
        top = tc_mar.find("./w:top", namespaces=NS)
        right = tc_mar.find("./w:right", namespaces=NS)
        bottom = tc_mar.find("./w:bottom", namespaces=NS)
        left = tc_mar.find("./w:left", namespaces=NS)
        vals = []
        for edge in [top, right, bottom, left]:
            if edge is None:
                vals.append("4px")
            else:
                try:
                    vals.append(f"{round(int(edge.get(wtag('w'), '80')) / 15)}px")
                except ValueError:
                    vals.append("4px")
        style["padding"] = " ".join(vals)

    shd = tcpr.find("./w:shd", namespaces=NS)
    if shd is not None:
        fill = shd.get(wtag("fill"))
        if fill and fill not in {"auto", "FFFFFF"}:
            style["background"] = f"#{fill}"

    borders = tcpr.find("./w:tcBorders", namespaces=NS)
    if borders is not None:
        for edge_name, css_name in [
            ("top", "border-top"),
            ("right", "border-right"),
            ("bottom", "border-bottom"),
            ("left", "border-left"),
        ]:
            border_css = border_to_css(borders.find(f"./w:{edge_name}", namespaces=NS))
            if border_css:
                style[css_name] = border_css

    # If any paragraph is centered/right-aligned, use that as cell default too.
    first_p = tc.find("./w:p", namespaces=NS)
    if first_p is not None:
        ppr = first_p.find("./w:pPr", namespaces=NS)
        if ppr is not None:
            jc = ppr.find("./w:jc", namespaces=NS)
            if jc is not None:
                align = ALIGN_MAP.get(jc.get(wtag("val"), "left"), "left")
                style["text-align"] = align
    return style



def parse_table(tbl: etree._Element) -> Table:
    grid_cols = []
    for grid_col in tbl.findall("./w:tblGrid/w:gridCol", namespaces=NS):
        try:
            grid_cols.append(int(grid_col.get(wtag("w"), "0")))
        except ValueError:
            grid_cols.append(0)

    active_vmerge: Dict[int, Cell] = {}
    rows: List[Row] = []

    for tr in tbl.findall("./w:tr", namespaces=NS):
        row = Row()
        cursor = 0
        new_active: Dict[int, Cell] = {}
        for tc in tr.findall("./w:tc", namespaces=NS):
            tcpr = tc.find("./w:tcPr", namespaces=NS)
            grid_span = 1
            vmerge = None
            if tcpr is not None:
                gs = tcpr.find("./w:gridSpan", namespaces=NS)
                if gs is not None:
                    try:
                        grid_span = int(gs.get(wtag("val"), "1"))
                    except ValueError:
                        grid_span = 1
                vm = tcpr.find("./w:vMerge", namespaces=NS)
                if vm is not None:
                    vmerge = vm.get(wtag("val"), "continue") or "continue"

            if vmerge == "continue":
                anchor = active_vmerge.get(cursor)
                if anchor is None:
                    # Fallback: try to locate the anchor within the spanned range.
                    for offset in range(grid_span):
                        anchor = active_vmerge.get(cursor + offset)
                        if anchor is not None:
                            break
                if anchor is not None:
                    anchor.rowspan += 1
                    for c in range(cursor, cursor + anchor.colspan):
                        new_active[c] = anchor
                cursor += anchor.colspan if anchor is not None else grid_span
                continue

            cell = Cell(
                col=cursor,
                colspan=grid_span,
                rowspan=1,
                text_html=parse_cell_text(tc),
                style=parse_cell_style(tc),
            )
            row.cells.append(cell)
            if vmerge == "restart":
                for c in range(cursor, cursor + grid_span):
                    new_active[c] = cell
            cursor += grid_span

        active_vmerge = new_active
        rows.append(row)

    return Table(rows=rows, col_widths_twips=grid_cols)



def strip_html(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return normalize_whitespace(html.unescape(s))



def infer_header_rows(table: Table) -> int:
    count = 0
    for row in table.rows[:8]:
        cells = row.cells
        if not cells:
            break
        texts = [strip_html(c.text_html) for c in cells]
        nonempty = [t for t in texts if t]
        nonempty_ratio = len(nonempty) / max(len(cells), 1)
        avg_len = sum(len(t) for t in nonempty) / max(len(nonempty), 1)
        has_merge = any(c.colspan > 1 or c.rowspan > 1 for c in cells)
        is_short_dense = nonempty_ratio >= 0.75 and avg_len <= 18
        if has_merge or is_short_dense:
            count += 1
        else:
            break
    return count



def style_dict_to_str(style: Dict[str, str]) -> str:
    order = [
        "width",
        "min-width",
        "text-align",
        "vertical-align",
        "padding",
        "background",
        "border-top",
        "border-right",
        "border-bottom",
        "border-left",
        "font-weight",
    ]
    parts = []
    for key in order:
        if key in style:
            parts.append(f"{key}: {style[key]}")
    for key, value in style.items():
        if key not in order:
            parts.append(f"{key}: {value}")
    return "; ".join(parts)



def table_has_visible_borders(table: Table) -> bool:
    border_count = 0
    vertical_or_top = 0
    cell_count = 0
    for row in table.rows:
        for cell in row.cells:
            cell_count += 1
            for key in ("border-top", "border-right", "border-bottom", "border-left"):
                value = cell.style.get(key)
                if value and value != "none":
                    border_count += 1
                    if key in {"border-top", "border-right", "border-left"}:
                        vertical_or_top += 1
    if cell_count == 0:
        return False
    # Layout tables in Word often use only a couple of bottom borders as fill-in lines.
    # Those should not get an extra rectangular outer border in HTML.
    if vertical_or_top == 0 and border_count <= max(2, cell_count // 2):
        return False
    return border_count > 0


def render_table(table: Table, table_number: int, header_rows_override: Optional[int]) -> str:
    col_widths_pct = twips_to_pct(table.col_widths_twips)
    header_rows = header_rows_override if header_rows_override is not None else infer_header_rows(table)

    out: List[str] = []
    table_class = "docx-table has-borders" if table_has_visible_borders(table) else "docx-table"
    out.append(f'<table class="{table_class}">')
    if col_widths_pct:
        out.append("<colgroup>")
        for pct in col_widths_pct:
            out.append(f'<col style="width: {pct:.2f}%;">')
        out.append("</colgroup>")

    # Не режем таблицу на thead/tbody: для DOCX-таблиц с вертикальными merge
    # это часто даёт перекос сетки, потому что rowspan не должен пересекать
    # границы row-group в HTML.
    if header_rows > 0:
        render_rows(out, table.rows[:header_rows], as_header=True)
    if header_rows < len(table.rows):
        render_rows(out, table.rows[header_rows:], as_header=False)

    out.append("</table>")
    return "\n".join(out)


def render_rows(out: List[str], rows: List[Row], as_header: bool) -> None:
    cell_tag = "th" if as_header else "td"
    for row in rows:
        out.append("<tr>")
        for cell in row.cells:
            attrs = []
            if cell.colspan > 1:
                attrs.append(f' colspan="{cell.colspan}"')
            if cell.rowspan > 1:
                attrs.append(f' rowspan="{cell.rowspan}"')
            style_str = style_dict_to_str(cell.style)
            attrs.append(f' style="{html.escape(style_str, quote=True)}"')
            out.append(f"<{cell_tag}{''.join(attrs)}>{cell.text_html}</{cell_tag}>")
        out.append("</tr>")



def parse_docx(docx_path: Path):
    with zipfile.ZipFile(docx_path) as zf:
        document_xml = zf.read("word/document.xml")
    root = etree.fromstring(document_xml)
    body = root.find("./w:body", namespaces=NS)
    if body is None:
        raise ValueError("word/document.xml does not contain w:body")

    blocks = []
    table_counter = 0
    for child in body:
        if child.tag == wtag("p"):
            html_text = parse_paragraph(child)
            text = strip_html(html_text)
            if text:
                blocks.append(("p", html_text))
        elif child.tag == wtag("tbl"):
            table_counter += 1
            blocks.append(("table", parse_table(child), table_counter))
    return blocks



def parse_header_rows_spec(spec: str) -> Dict[int, int]:
    result: Dict[int, int] = {}
    if not spec:
        return result
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        table_idx, header_rows = part.split(":", 1)
        result[int(table_idx)] = int(header_rows)
    return result


BASE_CSS = """
body {
  font-family: Arial, Helvetica, sans-serif;
  max-width: 1200px;
  margin: 24px auto;
  color: #000;
}
.docx-block + .docx-block {
  margin-top: 14px;
}
.docx-p {
  margin: 0;
  line-height: 1.2;
  white-space: pre-wrap;
}
.docx-p div {
  white-space: pre-wrap;
}
.docx-tab {
  display: inline-block;
  width: 4ch;
}
.docx-table {
  border-collapse: collapse;
  table-layout: fixed;
  width: 100%;
  margin: 8px 0 14px;
}
.docx-table.has-borders {
  border: 1px solid #000;
}
.docx-table th,
.docx-table td {
  font-size: 14px;
  line-height: 1.15;
  overflow-wrap: anywhere;
}
.docx-table th {
  font-weight: 700;
}
""".strip()


def convert(docx_path: Path, out_path: Path, header_rows_spec: str = "") -> None:
    blocks = parse_docx(docx_path)
    header_rows_map = parse_header_rows_spec(header_rows_spec)

    html_parts: List[str] = [
        "<!DOCTYPE html>",
        '<html lang="ru">',
        "<head>",
        '  <meta charset="utf-8">',
        f"  <title>{html.escape(docx_path.stem)}</title>",
        f"  <style>{BASE_CSS}</style>",
        "</head>",
        "<body>",
    ]

    for block in blocks:
        if block[0] == "p":
            html_parts.append(f'<div class="docx-block docx-p">{block[1]}</div>')
        else:
            _, table, table_number = block
            html_parts.append('<div class="docx-block">')
            html_parts.append(render_table(table, table_number, header_rows_map.get(table_number)))
            html_parts.append("</div>")

    html_parts.extend(["</body>", "</html>"])
    out_path.write_text("\n".join(html_parts), encoding="utf-8")



def main() -> None:
    parser = argparse.ArgumentParser(description="High-fidelity DOCX -> HTML converter for table-heavy documents.")
    parser.add_argument("input", type=Path, help="Path to input .docx")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Path to output .html")
    parser.add_argument(
        "--header-rows",
        default="",
        help='Optional per-table header row override, e.g. "2:4" or "1:2,2:4"',
    )
    args = parser.parse_args()
    convert(args.input, args.output, args.header_rows)


if __name__ == "__main__":
    main()

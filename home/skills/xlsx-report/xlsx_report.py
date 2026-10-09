"""Formatted .xlsx reports from pandas DataFrames - stacked blocks on a sheet.

Project-agnostic. A report is {sheet_name: [Block, ...]}; each Block is a titled
table. Blocks stack vertically with spacing, so a "scorecard on top, annual
figures below" layout is the default shape rather than something you hand-build.

    from xlsx_report import Block, write_report
    write_report("out.xlsx", {"Summary": [
        Block("Scorecard", df, label_col="Metric",
              formats={"Strategy": "signed_pct1", "Benchmark": "signed_pct1"}),
        Block("Calendar years", cal, formats={"*": "signed_pct1"}),
    ]}, title="Strategy report", subtitle="2007-01-02 to 2026-09-16")

Number formats (`formats={column: kind}`, `"*"` = every non-label column):
    pct1 pct2        12.3%             signed_pct1/2  +12.3% (green) / -4.5% (red)
    num0 num1 num2   12 / 12.3 / 1.23  signed_num2    +1.23 / -1.23, coloured
    int              1,234             bps            123 bps
    money0 money2    $1,234            text / date    passthrough / yyyy-mm-dd
Suffix any kind with "_plain" to keep the format but drop the +/- colouring.

Percent kinds expect PERCENT POINTS in (12.3 -> 12.3%); they are divided by 100
on write so the cell holds a real Excel percentage, not a string.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# --- palette: quiet, print-safe, readable on a projector ------------------- #
INK = "1F2933"          # body text
NAVY = "1F3A5F"         # report title bar
SLATE = "3E5C76"        # block title bar
HEAD_FILL = "E3E8EE"    # column-header band
BAND = "F5F7FA"         # zebra stripe
RULE = "C6CED6"         # borders
MUTED = "6B7A8C"        # notes
POS = "1A7F37"          # gains
NEG = "B42318"          # losses

_FMT = {
    "pct1": "0.0%;[Red]-0.0%", "pct2": "0.00%;[Red]-0.00%",
    "signed_pct1": "+0.0%;-0.0%", "signed_pct2": "+0.00%;-0.00%",
    "num0": "#,##0", "num1": "#,##0.0", "num2": "#,##0.00",
    "signed_num1": "+0.0;-0.0", "signed_num2": "+0.00;-0.00",
    "int": "#,##0", "bps": '#,##0" bps"',
    "money0": "$#,##0", "money2": "$#,##0.00",
    "date": "yyyy-mm-dd", "text": "@",
}
# kinds whose values get +/- colouring unless "_plain" is appended
_SIGNED = {"signed_pct1", "signed_pct2", "signed_num1", "signed_num2"}
# kinds stored as true Excel percentages (value divided by 100 on write)
_PCTLIKE = {"pct1", "pct2", "signed_pct1", "signed_pct2"}

_thin = Side(style="thin", color=RULE)
_BORDER = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)


@dataclass
class Block:
    """One titled table. `formats` maps column name -> kind; "*" covers the rest.

    `row_formats` is for TRANSPOSED tables - metrics down the side, one entity per
    column - where the format belongs to the row, not the column. Give one kind per
    body row; it overrides `formats` for every column except `label_col`.
    """
    title: str
    df: pd.DataFrame
    label_col: Optional[str] = None       # left-aligned, bold first column
    formats: Dict[str, str] = field(default_factory=dict)
    row_formats: Optional[List[str]] = None
    note: Optional[str] = None            # muted line under the table
    total_row: bool = False               # rule + bold on the last row
    chart: Optional[Dict[str, Any]] = None
    """Optional native Excel chart drawn from this block's own cells, so it stays
    live and editable in the workbook. Keys:
        kind    "bar" (default) | "col" | "line"
        cats    column name for the category axis (default: label_col)
        values  list of column names to plot (default: every non-label column)
        title   chart title            x_title / y_title  axis titles
        anchor  cell like "G4"; default is just right of the table
        width   cm (default 18)        height  cm (default 9)
        gap     bar gap % (default 6 - histogram bars nearly touch)
    """


def _kind_for(block: Block, col: str, i: Optional[int] = None) -> str:
    if col == block.label_col:
        return "text"
    if block.row_formats is not None and i is not None and i < len(block.row_formats):
        return block.row_formats[i]
    if col in block.formats:
        return block.formats[col]
    return block.formats.get("*", "num2")


_SERIES_COLORS = ("3E5C76", "1A7F37", "B42318", "946200", "5B4B8A", "1F3A5F")


def _add_chart(ws, block: Block, header_row: int, first_row: int, last_row: int) -> None:
    """Draw block.chart from the cells just written (header_row..last_row)."""
    from openpyxl.chart import BarChart, LineChart, Reference

    spec = block.chart or {}
    cols = list(block.df.columns)
    cat_col = spec.get("cats", block.label_col) or cols[0]
    val_cols = spec.get("values") or [c for c in cols if c != cat_col]
    if cat_col not in cols or not val_cols:
        return

    kind = spec.get("kind", "bar")
    chart = LineChart() if kind == "line" else BarChart()
    if isinstance(chart, BarChart):
        chart.type = "col"
        chart.gapWidth = int(spec.get("gap", 6))
        chart.overlap = 100 if len(val_cols) == 1 else -10
    chart.title = spec.get("title") or block.title
    chart.x_axis.title = spec.get("x_title")
    chart.y_axis.title = spec.get("y_title")
    chart.width = float(spec.get("width", 18))
    chart.height = float(spec.get("height", 9))
    chart.style = 2

    cats = Reference(ws, min_col=cols.index(cat_col) + 1, min_row=first_row, max_row=last_row)
    for i, vc in enumerate(val_cols):
        if vc not in cols:
            continue
        j = cols.index(vc) + 1
        chart.add_data(Reference(ws, min_col=j, min_row=header_row, max_row=last_row),
                       titles_from_data=True)
        s = chart.series[-1]
        colour = _SERIES_COLORS[i % len(_SERIES_COLORS)]
        if isinstance(chart, BarChart):
            s.graphicalProperties.solidFill = colour
            s.graphicalProperties.line.solidFill = colour
        else:
            s.graphicalProperties.line.solidFill = colour
            s.graphicalProperties.line.width = 20000
            s.smooth = False
    chart.set_categories(cats)
    if len(val_cols) == 1:
        chart.legend = None
    ws.add_chart(chart, spec.get("anchor") or f"{get_column_letter(len(cols) + 2)}{header_row}")


def _write_block(ws, block: Block, row: int, width_acc: Dict[int, float]) -> int:
    df = block.df
    ncol = len(df.columns)
    if ncol == 0:
        return row

    # --- block title bar ---
    ws.cell(row=row, column=1, value=block.title)
    for c in range(1, ncol + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = PatternFill("solid", fgColor=SLATE)
        cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[row].height = 20
    row += 1

    # --- column headers ---
    for j, col in enumerate(df.columns, start=1):
        cell = ws.cell(row=row, column=j, value=str(col))
        cell.fill = PatternFill("solid", fgColor=HEAD_FILL)
        cell.font = Font(name="Calibri", size=10, bold=True, color=INK)
        cell.alignment = Alignment(horizontal="left" if col == block.label_col else "right",
                                   vertical="center", wrap_text=True)
        cell.border = _BORDER
        # Headers wrap, so a header longer than its column costs height, not legibility. Only the
        # label column is allowed to be wide on the strength of its header.
        width_acc[j] = max(width_acc.get(j, 0),
                           min(len(str(col)) + 2, 34 if col == block.label_col else 18))
    ws.row_dimensions[row].height = 28
    row += 1

    # --- body ---
    n = len(df)
    for i, (_, rec) in enumerate(df.iterrows()):
        banded = (i % 2 == 1)
        is_total = block.total_row and i == n - 1
        for j, col in enumerate(df.columns, start=1):
            kind = _kind_for(block, col, i)
            plain = kind.endswith("_plain")
            base = kind[:-6] if plain else kind
            val = rec[col]

            missing = val is None or (isinstance(val, float) and pd.isna(val)) or \
                (not isinstance(val, (str, bytes)) and pd.isna(val) is True)
            if missing:
                val = "—"
            elif base in _PCTLIKE and isinstance(val, (int, float)) and not isinstance(val, bool):
                val = float(val) / 100.0
            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                val = float(val)

            cell = ws.cell(row=row, column=j, value=val)
            is_num = isinstance(val, float)
            cell.number_format = _FMT.get(base, "General") if is_num else "@"
            colour = INK
            if base in _SIGNED and not plain and is_num:
                colour = POS if val >= 0 else NEG
            cell.font = Font(name="Calibri", size=10, color=colour,
                             bold=bool(is_total or col == block.label_col))
            cell.alignment = Alignment(horizontal="left" if col == block.label_col else "right")
            cell.border = _BORDER
            if banded and not is_total:
                cell.fill = PatternFill("solid", fgColor=BAND)
            if is_total:
                cell.border = Border(left=_thin, right=_thin, bottom=_thin,
                                     top=Side(style="medium", color=SLATE))
            shown = f"{val:,.2f}" if is_num else str(val)
            # Cap the data-driven width per column KIND. Uncapped, one long prose cell (a hedge
            # description, a fee note) stretched its column to the sheet-wide maximum and pushed
            # every numeric column off screen, which is the opposite of what a scorecard is for.
            cap = 34 if col == block.label_col else (30 if base == "text" else 16)
            width_acc[j] = max(width_acc.get(j, 0), min(len(shown) + 2, cap))
        row += 1

    if block.chart:
        _add_chart(ws, block, header_row=row - n - 1, first_row=row - n, last_row=row - 1)

    if block.note:
        cell = ws.cell(row=row, column=1, value=block.note)
        cell.font = Font(name="Calibri", size=9, italic=True, color=MUTED)
        cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=max(ncol, 2))
        ws.row_dimensions[row].height = 26
        row += 1

    return row + 1     # blank spacer row between blocks


def write_report(path, sheets: Dict[str, List[Block]], title: Optional[str] = None,
                 subtitle: Optional[str] = None, freeze: bool = True) -> Any:
    """Write `sheets` to `path` (a filename or a file-like object). Returns `path`."""
    wb = Workbook()
    wb.remove(wb.active)

    for sheet_name, blocks in sheets.items():
        ws = wb.create_sheet(title=str(sheet_name)[:31])
        ws.sheet_view.showGridLines = False
        row = 1
        span = max((len(b.df.columns) for b in blocks if len(b.df.columns)), default=2)

        if title:
            ws.cell(row=row, column=1, value=title)
            for c in range(1, span + 1):
                cell = ws.cell(row=row, column=c)
                cell.fill = PatternFill("solid", fgColor=NAVY)
                cell.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
                cell.alignment = Alignment(vertical="center")
            ws.row_dimensions[row].height = 26
            row += 1
        if subtitle:
            cell = ws.cell(row=row, column=1, value=subtitle)
            cell.font = Font(name="Calibri", size=9.5, italic=True, color=MUTED)
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
            row += 1
        if title or subtitle:
            row += 1

        widths: Dict[int, float] = {}
        first_top = row
        for block in blocks:
            row = _write_block(ws, block, row, widths)

        for j, w in widths.items():
            ws.column_dimensions[get_column_letter(j)].width = min(max(w, 8), 34)
        if freeze and blocks:
            ws.freeze_panes = ws.cell(row=first_top + 2, column=2)
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.sheet_properties.pageSetUpPr.fitToPage = True

    wb.save(path)
    return path

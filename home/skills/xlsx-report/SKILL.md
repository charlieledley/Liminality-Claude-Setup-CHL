---
name: xlsx-report
description: Build formatted .xlsx reports from pandas DataFrames - stacked titled blocks, per-row or per-column number formats, native Excel charts. Includes a strategy/fund performance scorecard (CAGR, Sharpe, Sortino, Calmar, beta-adjusted attribution, calendar years) and a distribution analysis (auto-binned histogram, summary stats, percentile ladder). Use whenever the deliverable is an Excel workbook that a person will read, or when asked to describe or compare distributions.
---

# Formatted Excel reports

Three modules, in `~/.claude/skills/xlsx-report/`. Copy the ones you need next to the
calling code (they are plain files with no package install), or add the directory to
`sys.path`. Requires `openpyxl` and `pandas`.

| Module | Role | Project-specific? |
|---|---|---|
| `xlsx_report.py` | formatting engine - blocks, styles, charts | no |
| `perf_metrics.py` | strategy/fund scorecard metrics | no |
| `distribution.py` | histogram, summary stats, percentiles | no |

## The shape

A report is `{sheet_name: [Block, ...]}`. Blocks stack down the sheet with spacing,
so "summary on top, detail below" is the default layout rather than something you
position by hand.

```python
from xlsx_report import Block, write_report

write_report("out.xlsx", {"Summary": [
    Block("Scorecard", score_df, label_col="Metric", row_formats=kinds),
    Block("Calendar-year returns", cal_df, label_col="Year",
          formats={"*": "signed_pct1"}),
]}, title="Strategy summary", subtitle="2007-01-02 to 2026-09-16")
```

**Number formats.** `formats={column: kind}` with `"*"` as the catch-all. Use
`row_formats=[kind, ...]` instead for transposed tables - metrics down the side, one
column per entity - where the format belongs to the row. Kinds: `pct1 pct2
signed_pct1 signed_pct2 num0 num1 num2 signed_num1 signed_num2 int bps money0 money2
date text`. Signed kinds colour green/red; append `_plain` to keep the format without
the colour.

**Percent kinds take percent POINTS** (`12.3` -> `12.3%`) and divide by 100 on write,
so the cell holds a real number Excel can chart and recompute, never a string.

**Charts.** `Block(..., chart={"kind": "bar", "cats": "Bin", "values": [...]})` draws
a native Excel chart from the block's own cells - it stays live and editable in the
workbook rather than being a pasted image.

## Performance scorecard

`perf_metrics.scorecard(nav, benches, rf, ba_bench, maxloss, comp, hedge_phasing)`
returns one strategy's full row set; `to_frame({name: card})` turns several into a
metric-per-row DataFrame, and `row_kinds()` gives the matching `row_formats`.

Rows: CAGR, volatility, Sharpe, Sortino, max drawdown, Calmar, beta vs two named
benchmarks on two bases (calendar-month returns, the headline, and daily returns, each
labelled; `beta_monthly()` and `beta()`), median/worst/best calendar year, max and average of the max-possible-loss
series, then the beta-adjusted block - benchmark CAGR scaled by beta, excess CAGR over
it, count of calendar years out/underperforming it, average out/underperformance, and
worst underperformance.

**The beta-adjusted idea:** strip out the return earned merely by carrying market
beta, and see what is left. Full-period MONTHLY beta is applied to every calendar year - one
stable exposure estimate, rather than a per-year beta that would be noise on ~250
observations. `rf` is a DECIMAL annual rate (`0.042`), everything else is percent
points.

A good sanity check: run a price index against its own total-return version. Excess
CAGR should come out as minus the dividend yield, and every calendar year should
underperform.

## Distribution analysis

`distribution.distribution_blocks({name: values, ...}, value_fmt=, unit=)` returns the
three blocks: histogram with chart, summary statistics (count, mean, median, std dev,
min, max), and the percentile ladder (MAX, 99th, 97.5th, 95th, 90th, 75th, 50th, 25th,
10th, MIN). Pass several populations to compare them side by side.

**Binning is automatic** - Freedman-Diaconis (`2*IQR/n**(1/3)`), which keys off the
interquartile range and so is not dragged around by outliers the way Sturges or a
fixed count is. Falls back to Sturges when `n < 30` or the data is heavily tied, and
clamps to [5, 60].

Comparing populations shares one set of bins across them and switches the bars to
percent-of-population, so groups of different sizes stay comparable.

**Heavy tails:** the bin range defaults to clipping at the 0.5-99.5 percentile band,
with values beyond counted into the end bins (labelled with a leading `<=` / `>=`).
Without it, one outlier stretches the axis until every real observation collapses into
a single bar. Nothing is discarded, and the statistics and percentile tables always use
the full unclipped data. Pass `clip_pct=None` for raw min/max.

## Conventions

- Always `.xlsx`. Legacy `.xls` cannot carry most of this formatting.
- Write to a gitignored output directory. Committed workbooks churn forever in git
  because Office rewrites sensitivity-label metadata on every open.
- Blocks accept an empty DataFrame and are skipped, so an absent section is not an error.

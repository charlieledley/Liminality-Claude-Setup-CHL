"""Distribution description - histogram, summary stats and a percentile table.

Works on one population or several compared side by side. When several are given
they share one set of bins (computed over the pooled data) so the histogram bars
are actually comparable rather than each population using its own scale.

    import distribution as dist
    blocks = dist.distribution_blocks({"Strategy": a, "Benchmark": b},
                                      value_fmt="signed_pct1", unit="return")
    xlsx_report.write_report("dist.xlsx", {"Distribution": blocks}, title="...")

Bin count is chosen automatically by the Freedman-Diaconis rule - bin width
2*IQR/n**(1/3), which keys off the interquartile range and so is not dragged
around by a couple of outliers the way Sturges or a fixed count is. For small or
degenerate samples (n < 30, or IQR = 0 because the data is heavily tied) it falls
back to Sturges, and the count is clamped to [5, 60] so the picture stays readable.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from xlsx_report import Block

# The percentile ladder, top-down. Asymmetric by design: denser in the upper tail.
PCTILE_ROWS: Sequence[Tuple[str, Optional[float]]] = (
    ("MAX", None), ("99th %-tile", 99.0), ("97.5th %-tile", 97.5), ("95th %-tile", 95.0),
    ("90th %-tile", 90.0), ("75th %-tile", 75.0), ("50th %-tile", 50.0),
    ("25th %-tile", 25.0), ("10th %-tile", 10.0), ("MIN", None),
)

SUMMARY_ROWS = ("Count", "Mean", "Median", "Std dev", "Min", "Max")

Population = Union[Sequence[float], np.ndarray, pd.Series]


def _clean(x: Population) -> np.ndarray:
    a = pd.Series(x).astype(float).replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    return a


def bin_count(data: np.ndarray) -> int:
    """Freedman-Diaconis bin count, with a Sturges fallback; clamped to [5, 60]."""
    n = data.size
    if n < 2:
        return 1
    q75, q25 = np.percentile(data, [75, 25])
    iqr = q75 - q25
    spread = data.max() - data.min()
    if spread <= 0:
        return 1
    if n >= 30 and iqr > 0:
        width = 2.0 * iqr / (n ** (1.0 / 3.0))
        k = int(np.ceil(spread / width)) if width > 0 else 0
    else:
        k = int(np.ceil(np.log2(n) + 1))          # Sturges
    return int(min(max(k, 5), 60))


def histogram(pops: Dict[str, Population], bins: Optional[int] = None,
              density: bool = False,
              clip_pct: Optional[Tuple[float, float]] = None) -> pd.DataFrame:
    """Shared-bin histogram. Returns a frame: Bin | <pop1> | <pop2> ...

    `density=True` gives percent-of-population per bin, which is the honest way to
    compare groups of different sizes; counts are the default for a single group.

    `clip_pct=(0.5, 99.5)` sets the BIN RANGE from those percentiles instead of the
    raw min/max, and piles everything beyond into the end bins (labelled with a
    leading/trailing sign). On heavy-tailed data one outlier otherwise stretches
    the axis until every real observation collapses into a single bar. Nothing is
    discarded - the counts still add to n, and the stats and percentile tables
    always use the full, unclipped data.
    """
    cleaned = {k: _clean(v) for k, v in pops.items()}
    cleaned = {k: v for k, v in cleaned.items() if v.size}
    if not cleaned:
        return pd.DataFrame()
    pooled = np.concatenate(list(cleaned.values()))
    k = bins or bin_count(pooled)
    if clip_pct:
        lo, hi = (float(x) for x in np.percentile(pooled, list(clip_pct)))
        if hi <= lo:
            lo, hi = float(pooled.min()), float(pooled.max())
    else:
        lo, hi = float(pooled.min()), float(pooled.max())
    if hi <= lo:
        hi = lo + 1.0
    edges = np.linspace(lo, hi, k + 1)
    clipped_lo = bool(clip_pct) and pooled.min() < lo
    clipped_hi = bool(clip_pct) and pooled.max() > hi

    width = edges[1] - edges[0]
    dec = max(0, min(4, int(np.ceil(-np.log10(width))) + 1)) if width > 0 else 2
    labels = [f"{edges[i]:,.{dec}f} to {edges[i+1]:,.{dec}f}" for i in range(k)]
    if clipped_lo:
        labels[0] = f"≤ {edges[1]:,.{dec}f}"
    if clipped_hi:
        labels[-1] = f"≥ {edges[-2]:,.{dec}f}"

    out = {"Bin": labels}
    for name, arr in cleaned.items():
        # clip into the end bins so nothing is dropped and the counts still sum to n
        counts, _ = np.histogram(np.clip(arr, lo, hi) if clip_pct else arr, bins=edges)
        out[name] = (counts / counts.sum() * 100.0) if (density and counts.sum()) else counts
    return pd.DataFrame(out)


def summary_stats(pops: Dict[str, Population]) -> pd.DataFrame:
    """Statistic | <pop1> | <pop2> ... for count, mean, median, std dev, min, max."""
    rows = []
    cleaned = {k: _clean(v) for k, v in pops.items()}
    for label in SUMMARY_ROWS:
        rec: Dict[str, object] = {"Statistic": label}
        for name, a in cleaned.items():
            if not a.size:
                rec[name] = float("nan")
            elif label == "Count":
                rec[name] = float(a.size)
            elif label == "Mean":
                rec[name] = float(a.mean())
            elif label == "Median":
                rec[name] = float(np.median(a))
            elif label == "Std dev":
                rec[name] = float(a.std(ddof=1)) if a.size > 1 else float("nan")
            elif label == "Min":
                rec[name] = float(a.min())
            else:
                rec[name] = float(a.max())
        rows.append(rec)
    return pd.DataFrame(rows)


def percentile_table(pops: Dict[str, Population]) -> pd.DataFrame:
    """Level | <pop1> | <pop2> ... down the PCTILE_ROWS ladder, MAX to MIN."""
    rows = []
    cleaned = {k: _clean(v) for k, v in pops.items()}
    for label, q in PCTILE_ROWS:
        rec: Dict[str, object] = {"Level": label}
        for name, a in cleaned.items():
            if not a.size:
                rec[name] = float("nan")
            elif label == "MAX":
                rec[name] = float(a.max())
            elif label == "MIN":
                rec[name] = float(a.min())
            else:
                rec[name] = float(np.percentile(a, q))
        rows.append(rec)
    return pd.DataFrame(rows)


def distribution_blocks(pops: Dict[str, Population],
                        value_fmt: str = "num2",
                        unit: str = "value",
                        bins: Optional[int] = None,
                        density: Optional[bool] = None,
                        clip_pct: Optional[Tuple[float, float]] = (0.5, 99.5),
                        chart: bool = True) -> List[Block]:
    """The three blocks - histogram (with chart), summary stats, percentile ladder.

    `value_fmt` is the xlsx_report kind for the DATA values (percentiles and stats),
    e.g. "signed_pct1" for returns or "num2" for raw numbers. Counts always print
    as integers regardless.
    """
    if not isinstance(pops, dict):
        pops = {"Population": pops}
    multi = len(pops) > 1
    use_density = multi if density is None else density

    hist = histogram(pops, bins=bins, density=use_density, clip_pct=clip_pct)
    blocks: List[Block] = []

    if len(hist):
        k = len(hist)
        blocks.append(Block(
            title=f"Distribution — histogram ({k} bins, Freedman-Diaconis)",
            df=hist, label_col="Bin",
            formats={"*": "pct1" if use_density else "int"},
            chart={"kind": "bar", "cats": "Bin",
                   "title": f"Distribution of {unit}" + (" (% of population)" if use_density else " (count)"),
                   "x_title": unit, "y_title": "% of population" if use_density else "count",
                   "width": 24, "height": 10.5} if chart else None,
            note=("Bin count chosen by the Freedman-Diaconis rule (bin width 2·IQR/n⅓), which "
                  "keys off the interquartile range and so is not distorted by a few outliers."
                  + (" All populations share one set of bins, and bars show each population's own "
                     "percentage, so groups of different sizes stay comparable." if multi else "")
                  + (f" Bin range is clipped to the {clip_pct[0]:g}-{clip_pct[1]:g} percentile band "
                     "and values beyond it are counted in the end bins (≤ / ≥), so a lone "
                     "outlier cannot flatten the picture. Statistics and percentiles below use the "
                     "full unclipped data." if clip_pct else ""))))

    blocks.append(Block(title="Summary statistics", df=summary_stats(pops), label_col="Statistic",
                        row_formats=["int"] + [value_fmt] * (len(SUMMARY_ROWS) - 1)))
    blocks.append(Block(title="Percentiles", df=percentile_table(pops), label_col="Level",
                        formats={"*": value_fmt},
                        note="Linear interpolation between order statistics (NumPy default)."))
    return blocks

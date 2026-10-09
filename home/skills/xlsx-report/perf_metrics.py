"""Strategy scorecard metrics - risk, calendar-year, and beta-adjusted attribution.

Standalone: takes a NAV series (any base) plus benchmark price series and returns
an ordered scorecard. No dependency on any particular backtester.

    import perf_metrics as pm
    rows = pm.scorecard(nav, {"XNDX": xndx, "SPTR": sptr}, rf=0.042,
                        ba_bench="SPTR", maxloss=ml_series)
    df = pm.to_frame({"Strategy": rows})

The beta-adjusted ("BA") block answers: after stripping the return the strategy
got merely by carrying market beta, what is left? Full-period beta is applied to
each calendar year - a single, stable exposure estimate rather than a per-year
beta that would be noisy on ~250 observations.

Beta is reported twice: on calendar-month returns (the headline, and the beta the
BA block uses) and on daily returns. Everything measured against a benchmark is
on the monthly basis; the strategy's own return and risk rows stay daily
(docs/decisions/0008-beta-sampling-convention.md).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

TRADING_DAYS = 252

# (key, label, xlsx_report format kind) - the canonical row order.
ROW_SPEC: Sequence[Tuple[str, str, str]] = (
    ("cagr",            "CAGR",                        "signed_pct1"),
    ("vol",             "Volatility (ann.)",           "pct1"),
    ("sharpe",          "Sharpe",                      "num2"),
    ("sortino",         "Sortino",                     "num2"),
    ("maxdd",           "Max drawdown",                "pct1"),
    ("calmar",          "Calmar",                      "num2"),
    ("beta_a_m",        "Beta vs {A} (monthly)",       "num2"),
    ("beta_b_m",        "Beta vs {B} (monthly)",       "num2"),
    ("beta_a",          "Beta vs {A} (daily)",         "num2"),
    ("beta_b",          "Beta vs {B} (daily)",         "num2"),
    ("cal_median",      "Median Cal yr",               "signed_pct1"),
    ("cal_worst",       "Worst Cal yr",                "signed_pct1"),
    ("cal_best",        "Best Cal yr",                 "signed_pct1"),
    ("ml_max",          "Max of max possible loss",    "pct1"),
    ("ml_avg",          "Avg max possible loss",       "pct1"),
    ("ba_cagr",         "Beta-adj bench CAGR (monthly beta)", "signed_pct1"),
    ("ba_excess",       "Excess CAGR vs beta-adj",     "signed_pct1"),
    ("ba_n_out",        "# cal yrs outperf (BA)",      "num0"),
    ("ba_n_under",      "# cal yrs underperf (BA)",    "num0"),
    ("ba_avg_out",      "Avg outperf yr (BA)",         "signed_pct1"),
    ("ba_avg_under",    "Avg underperf yr (BA)",       "signed_pct1"),
    ("ba_worst_under",  "Worst underperf (BA)",        "signed_pct1"),
    ("hedge_phasing",   "Hedge phasing",               "text"),
)


def _clean(s) -> pd.Series:
    return pd.Series(s).dropna().astype(float)


def cagr(nav: pd.Series) -> float:
    nav = _clean(nav)
    if len(nav) < 2 or nav.iloc[0] <= 0:
        return float("nan")
    yrs = max((nav.index[-1] - nav.index[0]).days / 365.25, 1e-9)
    growth = nav.iloc[-1] / nav.iloc[0]
    return (growth ** (1 / yrs) - 1) * 100.0 if growth > 0 else float("nan")


def vol(nav: pd.Series) -> float:
    r = _clean(nav).pct_change().dropna()
    return float(r.std(ddof=1) * np.sqrt(TRADING_DAYS) * 100.0) if len(r) > 1 else float("nan")


def max_drawdown(nav: pd.Series, comp: bool = True) -> float:
    nav = _clean(nav)
    if len(nav) < 2:
        return float("nan")
    if comp:
        return float((nav / nav.cummax() - 1.0).min() * 100.0)
    idx = nav / nav.iloc[0] * 100.0            # growth-of-100, additive basis
    return float((idx - idx.cummax()).min())


def beta(nav: pd.Series, bench: Optional[pd.Series]) -> float:
    """Beta on DAILY returns (cov/var, ddof=1), benchmark aligned to the NAV's calendar."""
    if bench is None:
        return float("nan")
    a = _clean(nav).pct_change().rename("a")
    b = _clean(pd.Series(bench).reindex(_clean(nav).index).ffill()).pct_change().rename("b")
    d = pd.concat([a, b], axis=1).dropna()
    if len(d) < 3:
        return float("nan")
    var = d["b"].var(ddof=1)
    return float(d["a"].cov(d["b"]) / var) if var and np.isfinite(var) and var > 0 else float("nan")


def beta_monthly(nav: pd.Series, bench: Optional[pd.Series]) -> float:
    """Beta on CALENDAR-MONTH returns: both series sampled at month end, then cov/var (ddof=1).
    Same construction as the dashboard scorecard. This is the headline beta: a hedge that is
    uncorrelated day to day but pays in the months equities fall only shows up at this horizon."""
    if bench is None:
        return float("nan")
    nav = _clean(nav)
    b = _clean(pd.Series(bench).reindex(nav.index).ffill())
    a = nav.resample("ME").last().pct_change().rename("a")
    b = b.resample("ME").last().pct_change().rename("b")
    d = pd.concat([a, b], axis=1, join="inner").dropna()
    if len(d) < 3:
        return float("nan")
    var = d["b"].var(ddof=1)
    return float(d["a"].cov(d["b"]) / var) if var and np.isfinite(var) and var > 0 else float("nan")


def calendar_year_returns(nav: pd.Series, comp: bool = True) -> pd.Series:
    """Percent return per calendar year, indexed by year (int).

    Compounded: geometric, first (partial) year anchored to the run's starting NAV.
    Non-compounded: additive change in the growth-of-100 index. Mirrors the
    convention used for on-screen calendar bars so exports agree with the app.
    """
    nav = _clean(nav)
    if len(nav) < 2:
        return pd.Series(dtype=float)
    ends = nav.resample("YE").last().dropna()
    if not len(ends):
        return pd.Series(dtype=float)
    prev = ends.shift(1)
    prev.iloc[0] = float(nav.iloc[0])
    out = (ends / prev - 1.0) * 100.0 if comp else (ends - prev)
    out.index = out.index.year
    return out


def scorecard(nav: pd.Series,
              benches: Dict[str, Optional[pd.Series]],
              rf: float = 0.0,
              ba_bench: Optional[str] = None,
              maxloss: Optional[pd.Series] = None,
              comp: bool = True,
              hedge_phasing: str = "—") -> Dict[str, object]:
    """One strategy's full scorecard as {row_key: value}.

    `benches` is an ordered dict of at most two {label: price series}; `rf` is a
    DECIMAL annual rate (0.042 = 4.2%). `maxloss` is the worst-case-gap series in
    percent of NAV (negative). Percent outputs are in percent POINTS.
    """
    nav = _clean(nav)
    labels = list(benches.keys())
    out: Dict[str, object] = {k: float("nan") for k, _, _ in ROW_SPEC}
    out["hedge_phasing"] = hedge_phasing
    if len(nav) < 2:
        return out

    c = cagr(nav)
    v = vol(nav)
    mdd = max_drawdown(nav, comp)
    out["cagr"], out["vol"], out["maxdd"] = c, v, mdd
    out["sharpe"] = (c / 100.0 - rf) / (v / 100.0) if v and np.isfinite(v) and v > 0 else float("nan")

    dr = nav.pct_change().dropna()
    neg = dr[dr < 0]
    dn = float(neg.std(ddof=1) * np.sqrt(TRADING_DAYS)) if len(neg) > 1 else float("nan")
    out["sortino"] = (c / 100.0 - rf) / dn if np.isfinite(dn) and dn > 0 else float("nan")
    out["calmar"] = (c / 100.0) / abs(mdd / 100.0) if np.isfinite(mdd) and mdd < 0 else float("nan")

    for slot, lbl in zip(("beta_a", "beta_b"), labels[:2]):
        out[slot] = beta(nav, benches.get(lbl))
        out[slot + "_m"] = beta_monthly(nav, benches.get(lbl))

    cal = calendar_year_returns(nav, comp)
    if len(cal):
        out["cal_median"] = float(cal.median())
        out["cal_worst"] = float(cal.min())
        out["cal_best"] = float(cal.max())

    if maxloss is not None:
        ml = _clean(maxloss)
        if len(ml):
            out["ml_max"] = float(ml.min())     # most negative = worst case
            out["ml_avg"] = float(ml.mean())

    # --- beta-adjusted attribution vs one chosen benchmark ---
    bname = ba_bench or (labels[0] if labels else None)
    bser = benches.get(bname) if bname else None
    if bser is not None:
        b = beta_monthly(nav, bser)          # monthly beta, decision 0008
        bal = pd.Series(bser).reindex(nav.index).ffill().dropna()
        if np.isfinite(b) and len(bal) > 1:
            out["ba_cagr"] = b * cagr(bal)
            out["ba_excess"] = c - out["ba_cagr"]
            bcal = calendar_year_returns(bal, comp)
            joint = pd.concat([cal.rename("s"), (b * bcal).rename("b")], axis=1).dropna()
            if len(joint):
                ex = joint["s"] - joint["b"]
                out["ba_n_out"] = float((ex > 0).sum())
                out["ba_n_under"] = float((ex < 0).sum())
                out["ba_avg_out"] = float(ex[ex > 0].mean()) if (ex > 0).any() else float("nan")
                out["ba_avg_under"] = float(ex[ex < 0].mean()) if (ex < 0).any() else float("nan")
                out["ba_worst_under"] = float(ex.min()) if len(ex) else float("nan")
    return out


def to_frame(cards: Dict[str, Dict[str, object]],
             bench_labels: Sequence[str] = ("Bench A", "Bench B"),
             label_col: str = "Metric") -> pd.DataFrame:
    """Scorecards -> one metric-per-row DataFrame, columns in the order given."""
    a = bench_labels[0] if len(bench_labels) > 0 else "Bench A"
    b = bench_labels[1] if len(bench_labels) > 1 else "Bench B"
    rows = []
    for key, label, _ in ROW_SPEC:
        rows.append({label_col: label.replace("{A}", str(a)).replace("{B}", str(b)),
                     **{col: card.get(key) for col, card in cards.items()}})
    return pd.DataFrame(rows)


def formats_for(columns: Sequence[str], label_col: str = "Metric") -> Dict[str, str]:
    """Per-ROW formats cannot be expressed column-wise, so callers that want exact
    per-metric formatting should split blocks; this returns a sane column default."""
    return {label_col: "text", "*": "num2"}


def row_kinds() -> List[str]:
    """Format kind per scorecard row, in ROW_SPEC order."""
    return [kind for _, _, kind in ROW_SPEC]

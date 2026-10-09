---
name: bbg-pull
description: Pull data from the Bloomberg terminal on this PC through the Desktop API (blpapi) - reference values, daily or monthly history, field-dictionary search, security search - and the hard-won map of which implied-vol series are reachable how. Use whenever data is missing from the shared database and Charlie has a terminal, before proposing a workaround; also when the terminal refuses to export to Excel.
---

# Bloomberg pulls through the Desktop API

`bbg.py` in this folder (`~/.claude/skills/bbg-pull/`) wraps `blpapi`: `session()`, `reference()`,
`history()`, `history_many()`, `field_search()`, `field_info()`, `instrument_search()`. Import it with
the folder on `sys.path`. `blpapi` 3.26 is installed in the project `.venv`
(`C:\Liminality-put-writing-strategy\.venv\Scripts\python`), not in the system Python. The terminal
must be running and logged in; the gateway is `bbcomm.exe` on `localhost:8194`.

```python
import sys; sys.path.insert(0, r"C:\Users\charlie\.claude\skills\bbg-pull")
import bbg
s = bbg.session()
ser, errs = bbg.history(s, "SX5E 3M 80 VOL BVOL Index", "PX_LAST", "20070102", "20091231")
```

Dates are `YYYYMMDD` strings. `history()` returns a pandas Series and a list of error strings; an empty
Series with no errors means the ticker/field is valid but has no data in the window, which is a
different fact from an invalid field, so print both.

## Working method

1. **Ask what the destination expects** (shape, tenor buckets, moneyness points) and pull exactly that.
   The shared database's vol grid is `security, business_date, expiry_bucket (30D..720D), moneyness,
   vol_value`; forwards are `security, business_date, expiry_bucket, forward_value`.
2. **Probe before pulling**: one ticker, one field, one month. Check the value against something known
   (the database, a chart the user printed).
3. **Find names, do not guess them.** `field_search("moneyness")` for field mnemonics,
   `field_info("IVOL_MATURITY")` for a field's documentation and override list,
   `instrument_search("SX5E BVOL")` for securities (this is the SECF screen; it found the BVOL tickers
   after fifteen guessed patterns failed).
4. **When a code is accepted, prove it changed the result.** Bloomberg does not reject some bad override
   values, it falls back silently. Compare the new series with a known one before trusting it.
5. **Save tidy CSVs into the repo** (`analysis/data/` in the Liminality project) with a `source` column,
   and hand the same files to the database owner for loading. Never write to the shared tables
   without being asked.
6. **Metering.** Desktop API data is licensed to the terminal user and counted (daily security x field
   hits, monthly historical data points). Tens of thousands of points is fine; millions is a
   conversation. Monthly periodicity where daily is not needed.

## The implied-volatility map (verified 2026-09-25 on SX5E and DAX)

| Route | What it is | History | Verdict |
|---|---|---|---|
| `<T>_IMPVOL_<M>%MNY_DF` fields, e.g. `3MTH_IMPVOL_80%MNY_DF` | LIVE engine, moneyness grid. Prefixes `30DAY 60DAY 3MTH 6MTH 12MTH 18MTH 24MTH`; 80 and 120 carry **no** `.0`, 90.0 .. 110.0 do | 90-110 from 2006; **80/120 only from 2010-10-19** for European indices | fine for 2010+, useless before |
| `IVOL_MONEYNESS` + overrides `IVOL_MATURITY`, `IVOL_MONEYNESS_LEVEL` | same LIVE numbers as above for **current** values | history **ignores the level override**: every level returns one series. `"1Y"`, `"1YR"`, `"2Y"` are accepted and silently return the 1M / 2M series; `"12M"` valid but empty before 2011; `"18M"`, `"24M"`, `"90D"` return nothing | current values only |
| **BVOL securities** `"<IDX> <T> <M> VOL BVOL Index"`, forwards `"<IDX> <T> FWD BVOL Index"` | the surface the terminal charts ("80.0% 3 Months BVOL"); `instrument_search("SX5E BVOL")` lists them, T in `1M 2M 3M 6M 9M 1Y 2Y`, M in `30 .. 300`, also `50D 25DP 10DC ATM` | daily back to 2007 on the terminal | **not reachable from this API**: every BVOL security, including SPX and FX ones, returns `Unknown/Invalid Security (code 43, BAD_SEC)`; the family is terminal-only here. Charlie exported the FWD BVOL series from the terminal into a workbook, so the terminal route works when Excel export is allowed for the series |

So for pre-2010 European wing vols the answer is the terminal, not the API. **The export that works**
(Charlie, 2026-09-25): on the chart, right-click, Copy / Export options, Copy data options, **Copy data
to clipboard**, then paste into Excel. That is how the BVOL forwards arrived. Excel export itself may
be refused for some series; the clipboard copy was not. Then convert to the database shape. `analysis/data/sx5e_dax_fwds_2007_2009.csv` is the worked example of that.

A copy of this skill lives in the project at `tools/bbg-pull/` so the repo and the hourly backup carry it.

## Other verified facts

- `ReferenceDataRequest` and `HistoricalDataRequest` work on indices and ETFs; option-level fields
  work on listed SPX options with the `SPX <MM/DD/YY> P<strike> Index` form (see the project memory
  note `bloomberg-desktop-api`).
- Peer ETF total returns: `TOT_RETURN_INDEX_GROSS_DVDS`, monthly, then align on `PeriodIndex`, not
  timestamps (project memory `monthly-period-alignment-trap`).
- Chart PDFs printed from the terminal contain no data, only a legend; render them with LibreOffice
  (`soffice --headless --convert-to png`) if the date range needs checking.

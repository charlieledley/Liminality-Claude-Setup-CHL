"""Bloomberg Desktop API helpers (blpapi), stdlib + pandas only.

Import from a script next to this file or with the skill directory on sys.path:

    import sys; sys.path.insert(0, r"C:\\Users\\charlie\\.claude\\skills\\bbg-pull")
    import bbg
    s = bbg.session()
    px, errs = bbg.history(s, "QQQ Equity", "TOT_RETURN_INDEX_GROSS_DVDS", "20070102", "20261231", period="MONTHLY")
    ref, errs = bbg.reference(s, ["SX5E Index"], ["SECURITY_NAME", "PX_LAST"])
    fields = bbg.field_search(s, "moneyness")            # find mnemonics
    info = bbg.field_info(s, "IVOL_MATURITY")            # documentation + override list
    secs = bbg.instrument_search(s, "SX5E BVOL")        # SECF-style security lookup

The terminal must be running and logged in on this machine (bbcomm.exe on localhost:8194). Every
call is metered against the terminal user's daily and monthly limits; keep pulls to what is needed.
"""
import time

import blpapi
import pandas as pd

HOST, PORT = "localhost", 8194


def session(services=("//blp/refdata",)):
    o = blpapi.SessionOptions()
    o.setServerHost(HOST)
    o.setServerPort(PORT)
    s = blpapi.Session(o)
    if not s.start():
        raise RuntimeError("could not start blpapi session: is the Bloomberg terminal running and logged in?")
    for svc in services:
        if not s.openService(svc):
            raise RuntimeError("could not open %s" % svc)
    return s


def pump(s, timeout=180):
    """Yield every message until the final RESPONSE event, or time out."""
    t0 = time.time()
    while True:
        ev = s.nextEvent(500)
        for msg in ev:
            yield msg
        if ev.eventType() == blpapi.Event.RESPONSE:
            return
        if time.time() - t0 > timeout:
            raise TimeoutError("blpapi request timed out after %ds" % timeout)


def _overrides(req, overrides):
    if overrides:
        ov = req.getElement("overrides")
        for k, v in overrides.items():
            o = ov.appendElement()
            o.setElement("fieldId", k)
            o.setElement("value", str(v))


def _field_exceptions(sd):
    errs = []
    if sd.hasElement("fieldExceptions"):
        fe = sd.getElement("fieldExceptions")
        for k in range(fe.numValues()):
            x = fe.getValue(k)
            errs.append("%s: %s" % (x.getElementAsString("fieldId"),
                                    x.getElement("errorInfo").getElementAsString("message")))
    return errs


def reference(s, tickers, fields, overrides=None, chunk=20):
    """Current values. Returns ({ticker: {field: value-as-string}}, {ticker or field: error})."""
    svc = s.getService("//blp/refdata")
    out, errs = {}, {}
    for i in range(0, len(tickers), chunk):
        r = svc.createRequest("ReferenceDataRequest")
        for t in tickers[i:i + chunk]:
            r.append("securities", t)
        for f in fields:
            r.append("fields", f)
        _overrides(r, overrides)
        s.sendRequest(r)
        for msg in pump(s):
            if not msg.hasElement("securityData"):
                continue
            arr = msg.getElement("securityData")
            for j in range(arr.numValues()):
                sd = arr.getValue(j)
                tk = sd.getElementAsString("security")
                if sd.hasElement("securityError"):
                    errs[tk] = sd.getElement("securityError").getElementAsString("message")
                    continue
                for e in _field_exceptions(sd):
                    errs[tk + " " + e.split(":")[0]] = e
                fd = sd.getElement("fieldData")
                out[tk] = {f: (fd.getElementAsString(f) if fd.hasElement(f) else None) for f in fields}
    return out, errs


def history(s, ticker, field, start, end, period="DAILY", overrides=None, fill="ACTIVE_DAYS_ONLY"):
    """One security, one field. Dates as YYYYMMDD strings. Returns (pd.Series indexed by Timestamp, [errors])."""
    svc = s.getService("//blp/refdata")
    r = svc.createRequest("HistoricalDataRequest")
    r.append("securities", ticker)
    r.append("fields", field)
    r.set("startDate", start)
    r.set("endDate", end)
    r.set("periodicitySelection", period)
    r.set("nonTradingDayFillOption", fill)
    _overrides(r, overrides)
    s.sendRequest(r)
    rows, errs = [], []
    for msg in pump(s):
        if msg.hasElement("responseError"):
            errs.append(msg.getElement("responseError").getElementAsString("message"))
            continue
        if not msg.hasElement("securityData"):
            continue
        sd = msg.getElement("securityData")
        if sd.hasElement("securityError"):
            errs.append(sd.getElement("securityError").getElementAsString("message"))
            continue
        errs += _field_exceptions(sd)
        fa = sd.getElement("fieldData")
        for k in range(fa.numValues()):
            e = fa.getValue(k)
            if e.hasElement(field):
                rows.append((pd.Timestamp(e.getElementAsDatetime("date")), e.getElementAsFloat(field)))
    ser = pd.Series(dict(rows), dtype=float).sort_index()
    ser.name = "%s %s" % (ticker, field)
    return ser, errs


def history_many(s, tickers, field, start, end, period="DAILY", overrides=None):
    """Several securities, one field -> (DataFrame date x ticker, {ticker: error})."""
    frames, errs = {}, {}
    for t in tickers:
        ser, e = history(s, t, field, start, end, period, overrides)
        if e:
            errs[t] = "; ".join(e)
        if len(ser):
            frames[t] = ser
    return pd.DataFrame(frames), errs


def field_search(s, text, want=None):
    """Search the field dictionary. Returns [(mnemonic, description)], optionally filtered by substrings."""
    if not s.openService("//blp/apiflds"):
        raise RuntimeError("could not open //blp/apiflds")
    svc = s.getService("//blp/apiflds")
    r = svc.createRequest("FieldSearchRequest")
    r.set("searchSpec", text)
    s.sendRequest(r)
    hits = []
    for msg in pump(s):
        if not msg.hasElement("fieldData"):
            continue
        fd = msg.getElement("fieldData")
        for i in range(fd.numValues()):
            info = fd.getValue(i).getElement("fieldInfo")
            hits.append((info.getElementAsString("mnemonic"), info.getElementAsString("description")))
    if want:
        want = [w.upper() for w in want]
        hits = [h for h in hits if any(w in h[0].upper() or w in h[1].upper() for w in want)]
    return hits


def field_info(s, mnemonic):
    """Documentation, datatype and override list for one field. Returns a dict or None."""
    if not s.openService("//blp/apiflds"):
        raise RuntimeError("could not open //blp/apiflds")
    svc = s.getService("//blp/apiflds")
    r = svc.createRequest("FieldInfoRequest")
    r.append("id", mnemonic)
    r.set("returnFieldDocumentation", True)
    s.sendRequest(r)
    for msg in pump(s):
        if not msg.hasElement("fieldData"):
            continue
        fd = msg.getElement("fieldData")
        for i in range(fd.numValues()):
            e = fd.getValue(i)
            if e.hasElement("fieldError"):
                return {"error": e.getElement("fieldError").getElementAsString("message")}
            info = e.getElement("fieldInfo")
            out = {"mnemonic": info.getElementAsString("mnemonic"),
                   "description": info.getElementAsString("description"),
                   "datatype": info.getElementAsString("datatype"),
                   "overrides": [], "documentation": ""}
            if info.hasElement("overrides"):
                ov = info.getElement("overrides")
                out["overrides"] = [ov.getValue(k) for k in range(ov.numValues())]
            if info.hasElement("documentation"):
                out["documentation"] = info.getElementAsString("documentation")
            return out
    return None


def instrument_search(s, query, max_results=25):
    """Security lookup (like SECF). Returns [(ticker, description)]."""
    if not s.openService("//blp/instruments"):
        raise RuntimeError("could not open //blp/instruments")
    svc = s.getService("//blp/instruments")
    r = svc.createRequest("instrumentListRequest")
    r.set("query", query)
    r.set("maxResults", max_results)
    s.sendRequest(r)
    hits = []
    for msg in pump(s):
        if msg.hasElement("results"):
            res = msg.getElement("results")
            for i in range(res.numValues()):
                e = res.getValue(i)
                hits.append((e.getElementAsString("security"), e.getElementAsString("description")))
    return hits

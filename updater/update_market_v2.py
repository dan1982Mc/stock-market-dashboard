"""Build current V2 market JSON from free public market data.

All external sources are optional and bounded: one unavailable provider must
never prevent the rest of the dashboard from updating.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import io
import json
import time
import warnings

import pandas as pd
import requests
import yfinance as yf

from config import (
    TICKERS, HISTORY_PERIOD, MA_LONG, MA_SHORT, OUTPUT_FILE, HISTORY_FILE,
    CAPE_FILE, FRED_INFLATION, FRED_EM_VOL,
)
from indicators import band, clean, trend_metrics, drawdown_series, current_drawdown, percentile
from scoring_v2 import market_brief, rules_placeholder

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {"User-Agent": "Mozilla/5.0 stock-market-dashboard/2.0"}
HTTP_TIMEOUT = (5, 10)
SOURCE_WORKERS = 4


def series_for(ticker):
    try:
        df = yf.download(
            ticker, period=HISTORY_PERIOD, interval="1d", auto_adjust=True,
            progress=False, threads=False, timeout=12,
        )
        if df.empty:
            print(f"Yahoo {ticker}: unavailable")
            return pd.Series(dtype=float)
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        s = pd.to_numeric(close, errors="coerce").dropna()
        print(f"Yahoo {ticker}: {len(s)} observations")
        return s
    except Exception as exc:
        print(f"Yahoo {ticker} failed: {exc}")
        return pd.Series(dtype=float)


def _http(url, verify=True):
    try:
        with requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT, verify=verify) as r:
            r.raise_for_status()
            return r.content
    except Exception as exc:
        raise RuntimeError(f"{url}: {exc}") from exc


def fred_series(series_id):
    """Fetch FRED data; accept DATE,SERIES and DATE,VALUE exports."""
    urls = [
        f"https://fred.stlouisfed.org/data/{series_id}.csv",
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
    ]
    for url in urls:
        try:
            raw = pd.read_csv(io.BytesIO(_http(url)))
            cols = {str(c).strip().lower(): c for c in raw.columns}
            date_col = cols.get("date") or cols.get("observation_date")
            value_col = next((c for c in raw.columns if str(c).strip().upper() == series_id.upper()), None)
            if value_col is None:
                value_col = next((c for c in raw.columns if str(c).strip().lower() == "value"), None)
            if date_col is None or value_col is None:
                raise ValueError(f"unexpected columns: {list(raw.columns)}")
            d = pd.to_datetime(raw[date_col], errors="coerce")
            v = pd.to_numeric(raw[value_col].astype(str).str.strip().replace({".": None, "": None, "nan": None}), errors="coerce")
            s = pd.Series(v.to_numpy(), index=d).dropna().sort_index()
            s = s[~s.index.duplicated(keep="last")]
            if len(s):
                print(f"FRED {series_id}: {len(s)} observations from {url}")
                return s
        except Exception as exc:
            print(f"FRED source failed {url}: {exc}")
    return pd.Series(dtype=float)


def vxeem_series():
    """Fetch VXEEM directly from Cboe, falling back to the FRED mirror."""
    urls = [
        "https://cdn.cboe.com/api/global/us_indices/daily_prices/VXEEM_History.csv",
    ]
    for url in urls:
        try:
            raw = pd.read_csv(io.BytesIO(_http(url)))
            raw.columns = [str(c).strip() for c in raw.columns]
            date_col = next((c for c in raw.columns if str(c).strip().lower() in ("date", "trade_date")), None)
            value_col = next((c for c in raw.columns if str(c).strip().upper() in ("VXEEM", "CLOSE", "VALUE")), None)
            if date_col is None or value_col is None:
                raise ValueError(f"unexpected Cboe columns: {list(raw.columns)}")
            d = pd.to_datetime(raw[date_col], errors="coerce")
            v = pd.to_numeric(raw[value_col], errors="coerce")
            s = pd.Series(v.to_numpy(), index=d).dropna().sort_index()
            s = s[~s.index.duplicated(keep="last")]
            if len(s) >= 20:
                print(f"VXEEM: {len(s)} observations from Cboe")
                return s
        except Exception as exc:
            print(f"Cboe VXEEM failed: {exc}")

    s = fred_series(FRED_EM_VOL)
    if len(s):
        print(f"VXEEM: {len(s)} observations from FRED mirror")
    else:
        print("VXEEM unavailable")
    return s


def vstoxx_series():
    """Fetch official STOXX V2TX history with a bounded SSL fallback."""
    urls = [
        "https://www.stoxx.com/document/Indices/Current/HistoricalData/h_v2tx.txt",
        "https://www.stoxx.com/document/Indices/Current/HistoricalData/vstoxx.txt",
    ]
    for url in urls:
        for verify in (True, False):
            try:
                if not verify:
                    warnings.filterwarnings("ignore", message="Unverified HTTPS request")
                text = _http(url, verify=verify).decode("utf-8", errors="replace")
                df = pd.read_csv(io.StringIO(text), sep=";", skip_blank_lines=True)
                df.columns = [str(c).strip() for c in df.columns]
                if not {"Date", "Indexvalue"}.issubset(df.columns):
                    df = pd.read_csv(io.StringIO(text), sep=";", skiprows=2)
                    df.columns = [str(c).strip() for c in df.columns]
                d = pd.to_datetime(df["Date"], format="%d.%m.%Y", errors="coerce")
                v = pd.to_numeric(df["Indexvalue"], errors="coerce")
                s = pd.Series(v.to_numpy(), index=d).dropna().sort_index()
                s = s[~s.index.duplicated(keep="last")]
                if len(s) >= 20:
                    print(f"VSTOXX: {len(s)} observations from STOXX")
                    return s
            except Exception as exc:
                print(f"VSTOXX source failed {url} verify={verify}: {exc}")
    print("VSTOXX unavailable")
    return pd.Series(dtype=float)


def _parse_shiller(content):
    """Parse Shiller's monthly workbook and use its published CAPE column."""
    candidates = []
    for skip in (0, 7, 8):
        raw = pd.read_excel(io.BytesIO(content), sheet_name="Data", header=None, skiprows=skip)
        if raw.empty or raw.shape[1] < 13:
            continue
        dates = pd.to_numeric(raw.iloc[:, 0], errors="coerce")
        cape = pd.to_numeric(raw.iloc[:, 12], errors="coerce")
        valid = dates.notna() & cape.notna()
        if valid.sum() < 100:
            continue
        years = dates[valid].astype(int)
        months = ((dates[valid] - years) * 100).round().astype(int).clip(1, 12)
        idx = pd.to_datetime({"year": years, "month": months, "day": 1}, errors="coerce")
        s = pd.Series(cape[valid].to_numpy(), index=idx).dropna().sort_index()
        s = s[~s.index.duplicated(keep="last")]
        if len(s) >= 100:
            candidates.append(s)
    if not candidates:
        raise ValueError("no valid CAPE column found")
    # Pick the candidate with the newest date; this avoids silently accepting a stale sheet layout.
    s = max(candidates, key=lambda x: x.index.max())
    return float(s.iloc[-1]), s


def load_cape():
    """Load Shiller CAPE; prefer the auto-updated mirror of Shiller's official file."""
    urls = [
        "https://raw.githubusercontent.com/posix4e/shiller_wrapper_data/main/ie_data.xls",
        "https://raw.githubusercontent.com/WealthyFranklin/shiller-cape-analysis/main/ie_data.xls",
        "https://img1.wsimg.com/blobby/go/e5e77e0b-59d1-44d9-ab25-4763ac982e53/downloads/e27e58c1-8ae0-488c-a976-a298708c7175/ie_data.xls",
        "https://www.econ.yale.edu/~shiller/data/ie_data.xls",
    ]
    for url in urls:
        try:
            current, series = _parse_shiller(_http(url))
            # Reject clearly stale vintages. The dashboard should not silently use an old CAPE.
            age_days = (pd.Timestamp.now() - series.index.max()).days
            if age_days > 180:
                raise ValueError(f"CAPE vintage is {age_days} days old")
            print(f"CAPE: {len(series)} observations, latest {current:.2f}, vintage {series.index.max().date()}")
            return current, series, "Robert Shiller dataset"
        except Exception as exc:
            print(f"CAPE source failed {url}: {exc}")
    try:
        obj = json.loads((ROOT / CAPE_FILE).read_text(encoding="utf-8"))
        v = obj.get("us")
        print("CAPE: using bundled fallback value")
        return v, pd.Series([v], dtype=float) if v is not None else pd.Series(dtype=float), obj.get("source", {}).get("us", "Bundled fallback")
    except Exception:
        return None, pd.Series(dtype=float), "Unavailable"


def metric(name, current, display, detail, hist_series, decimals=2):
    clean_series = hist_series.dropna() if isinstance(hist_series, pd.Series) else pd.Series(dtype=float)
    pct = percentile(current, clean_series) if current is not None and len(clean_series) else None
    return {"name": name, "current": clean(current, decimals), "display": display, "detail": detail,
            "percentile": pct, "percentile_label": f"P{int(pct)}" if pct is not None else None,
            "band": band(clean_series) if current is not None and len(clean_series) >= 20 else None}


def main():
    started = time.monotonic()
    now = datetime.now(timezone.utc)

    raw = {}
    with ThreadPoolExecutor(max_workers=SOURCE_WORKERS) as pool:
        futures = {pool.submit(series_for, ticker): key for key, ticker in TICKERS.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                raw[key] = future.result()
            except Exception as exc:
                print(f"Yahoo task {key} failed: {exc}")
                raw[key] = pd.Series(dtype=float)

    specialist = {}
    with ThreadPoolExecutor(max_workers=SOURCE_WORKERS) as pool:
        tasks = {
            pool.submit(vstoxx_series): "VSTOXX",
            pool.submit(vxeem_series): "EM_VIX",
            pool.submit(fred_series, FRED_INFLATION): "INFLATION",
            pool.submit(load_cape): "CAPE",
        }
        for future in as_completed(tasks):
            key = tasks[future]
            try:
                specialist[key] = future.result()
            except Exception as exc:
                print(f"Specialist task {key} failed: {exc}")

    raw["VSTOXX"] = specialist.get("VSTOXX", pd.Series(dtype=float))
    raw["EM_VIX"] = specialist.get("EM_VIX", pd.Series(dtype=float))
    inflation_hist = specialist.get("INFLATION", pd.Series(dtype=float))
    inflation = float(inflation_hist.iloc[-1]) if len(inflation_hist) else None
    cape, cape_hist, cape_source = specialist.get("CAPE", (None, pd.Series(dtype=float), "Unavailable"))

    trends = {k: trend_metrics(raw[k], MA_SHORT, MA_LONG) for k in ("ACWI", "US", "Europe", "EM")}
    trend_history = {k: (raw[k] / raw[k].rolling(MA_LONG).mean() - 1) * 100 for k in trends}
    dd = drawdown_series(raw["ACWI"])
    dd_now = current_drawdown(raw["ACWI"])

    equities = []
    for k, label in (("ACWI", "ACWI"), ("US", "US equities"), ("Europe", "Europe"), ("EM", "Emerging markets")):
        t = trends[k]
        equities.append(metric(label, t["current"] if t else None,
                                f"{t['current']:+.1f}% vs 200DMA" if t else "—",
                                f"50DMA {t['ma50']:.1f} · 200DMA {t['ma200']:.1f}" if t else "Insufficient history",
                                trend_history[k], 1))

    def vol(k, label):
        s = raw[k]
        v = float(s.iloc[-1]) if len(s) else None
        return metric(label, v, f"{v:.1f}" if v is not None else "—",
                      "30-day option-implied volatility index." if v is not None else "Data source unavailable.", s, 1)

    risk = [vol("VIX", "US volatility (VIX)"), vol("VSTOXX", "Europe volatility (VSTOXX)"),
            vol("EM_VIX", "Emerging-market volatility (VXEEM)"),
            metric("ACWI drawdown", dd_now, f"{dd_now:.1f}%" if dd_now is not None else "—",
                   "Distance from the running ACWI high.", dd, 1)]
    valuation = [metric("US CAPE", cape, f"{cape:.1f}" if cape is not None else "Unavailable",
                        f"Source: {cape_source}", cape_hist, 1)]

    us10 = raw["US10Y"]
    u10 = float(us10.iloc[-1]) if len(us10) else None
    gold = raw["GOLD"]
    g = float(gold.iloc[-1]) if len(gold) else None
    cross = [metric("US 10Y yield", u10, f"{u10:.2f}%" if u10 is not None else "—", "Treasury market yield proxy.", us10, 2),
             metric("Gold", g, f"${g:,.0f}" if g is not None else "—", "Gold futures price proxy.", gold, 0)]

    vix = float(raw["VIX"].iloc[-1]) if len(raw["VIX"]) else None
    vsto = float(raw["VSTOXX"].iloc[-1]) if len(raw["VSTOXX"]) else None
    emv = float(raw["EM_VIX"].iloc[-1]) if len(raw["EM_VIX"]) else None
    priced = [
        {"name": "Equity volatility already priced", "display": f"US {vix:.1f} VIX" if vix is not None else "Unavailable",
         "explanation": "Option prices embed near-term volatility; European and emerging-market volatility are shown alongside it."},
        {"name": "Inflation priced into bonds", "display": f"10Y breakeven {inflation:.2f}%" if inflation is not None else "Unavailable",
         "explanation": "10-year Treasury breakeven inflation is derived from nominal and inflation-indexed Treasury yields and is a market-implied inflation expectation."},
        {"name": "Equity valuation being paid", "display": f"CAPE {cape:.1f}" if cape is not None else "Unavailable",
         "explanation": "CAPE compares the S&P 500 price with ten years of inflation-adjusted earnings; a higher reading means investors are paying a higher historical earnings multiple."},
    ]

    dates = [raw[k].index[-1] for k in raw if len(raw[k])]
    if len(inflation_hist): dates.append(inflation_hist.index[-1])
    if len(cape_hist): dates.append(cape_hist.index[-1])
    latest = {
        "version": "2.0.6", "mode": "LIVE", "updated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "data_through": max(dates).strftime("%Y-%m-%d") if dates else None,
        "brief": market_brief(trends["ACWI"]["current"] if trends["ACWI"] else None, dd_now, vix, vsto, emv),
        "equities": equities, "risk": risk, "valuation": valuation, "cross_asset": cross,
        "priced_in": priced, "rules": rules_placeholder(),
        "sources": ["Yahoo Finance / yfinance", "Cboe VIX / VXEEM; FRED fallback", "STOXX VSTOXX official history", "FRED 10Y inflation breakeven", "Robert Shiller dataset"],
    }

    weekly = raw["ACWI"].resample("W-FRI").last().dropna()
    history = {"dates": [d.strftime("%Y-%m-%d") for d in weekly.index], "acwi": [clean(v, 2) for v in weekly.values]}
    (ROOT / OUTPUT_FILE).write_text(json.dumps(latest, indent=2), encoding="utf-8")
    (ROOT / HISTORY_FILE).write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE} and {HISTORY_FILE} in {time.monotonic() - started:.1f}s")


if __name__ == "__main__":
    main()

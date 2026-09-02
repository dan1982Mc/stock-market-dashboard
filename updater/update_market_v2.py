"""Build current V2 market JSON from free public market data.

The frontend never talks to external data providers. GitHub Actions runs this
script and commits data/latest.json and data/history.json.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import math
import urllib.request

import pandas as pd
import yfinance as yf

from config import TICKERS, HISTORY_PERIOD, MA_LONG, MA_SHORT, OUTPUT_FILE, HISTORY_FILE, CAPE_FILE, FRED_INFLATION
from indicators import band, clean, trend_metrics, drawdown_series, current_drawdown, percentile
from scoring_v2 import market_brief, rules_placeholder

ROOT = Path(__file__).resolve().parents[1]


def series_for(ticker):
    try:
        df = yf.download(ticker, period=HISTORY_PERIOD, interval="1d", auto_adjust=True, progress=False, threads=False)
        if df.empty:
            return pd.Series(dtype=float)
        close = df["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return pd.to_numeric(close, errors="coerce").dropna()
    except Exception as exc:
        print(f"Data error {ticker}: {exc}")
        return pd.Series(dtype=float)


def fred_latest(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        raw = pd.read_csv(url)
        raw["DATE"] = pd.to_datetime(raw["DATE"])
        raw[series_id] = pd.to_numeric(raw[series_id], errors="coerce")
        raw = raw.dropna(subset=[series_id])
        if raw.empty:
            return None, None, pd.Series(dtype=float)
        return float(raw.iloc[-1][series_id]), raw.iloc[-1]["DATE"].strftime("%Y-%m-%d"), raw.set_index("DATE")[series_id]
    except Exception as exc:
        print(f"FRED {series_id} unavailable: {exc}")
        return None, None, pd.Series(dtype=float)


def load_cape():
    # First try the Shiller/Yale workbook. If it fails, use the local manual file.
    url = "https://www.econ.yale.edu/~shiller/data/ie_data.xls"
    try:
        df = pd.read_excel(url, sheet_name="Data", skiprows=7)
        candidates = [c for c in df.columns if "CAPE" in str(c).upper() or "P/E10" in str(c).upper()]
        if candidates:
            values = pd.to_numeric(df[candidates[0]], errors="coerce").dropna()
            if not values.empty:
                return float(values.iloc[-1]), "Robert Shiller / Yale"
    except Exception as exc:
        print(f"Automatic CAPE unavailable: {exc}")
    try:
        obj = json.loads((ROOT / CAPE_FILE).read_text(encoding="utf-8"))
        return obj.get("us"), obj.get("source", {}).get("us", "Manual CAPE file")
    except Exception:
        return None, "Unavailable"


def safe_range(series):
    s = series.dropna()
    if len(s) < 20:
        return None
    return band(s)


def metric(name, current, display, detail, hist_series):
    return {"name":name,"current":clean(current,2),"display":display,"detail":detail,"percentile":percentile(current, hist_series) if current is not None else None,"percentile_label":f"P{int(percentile(current,hist_series))}" if current is not None and percentile(current,hist_series) is not None else None,"band":safe_range(hist_series) if current is not None else None}


def main():
    now = datetime.now(timezone.utc)
    raw = {key: series_for(ticker) for key,ticker in TICKERS.items()}

    # Some Yahoo volatility yield symbols are expressed on a 0-100 index scale.
    if not raw["US10Y"].empty:
        raw["US10Y"] = raw["US10Y"] / 10.0

    trends = {key: trend_metrics(raw[key], MA_SHORT, MA_LONG) for key in ("ACWI","US","Europe","EM")}
    trend_history = {}
    for key in ("ACWI","US","Europe","EM"):
        s = raw[key].dropna()
        trend_history[key] = (s / s.rolling(MA_LONG).mean() - 1) * 100

    dd = drawdown_series(raw["ACWI"])
    dd_now = current_drawdown(raw["ACWI"])

    cape, cape_source = load_cape()
    inflation, inflation_date, inflation_hist = fred_latest(FRED_INFLATION)

    def vol_metric(key, label):
        s = raw[key]
        now_v = float(s.iloc[-1]) if len(s) else None
        return metric(label, now_v, f"{now_v:.1f}" if now_v is not None else "—", "Current option-implied volatility index.", s)

    equities = []
    labels = {"ACWI":"ACWI","US":"US equities","Europe":"Europe","EM":"Emerging markets"}
    for key in ("ACWI","US","Europe","EM"):
        t = trends[key]
        equities.append(metric(labels[key], t["current"] if t else None, f"{t['current']:+.1f}% vs 200DMA" if t else "—", f"50DMA {t['ma50']:.1f} · 200DMA {t['ma200']:.1f}" if t else "Insufficient history", trend_history[key]))

    risk = [
        vol_metric("VIX", "US volatility (VIX)"),
        vol_metric("VSTOXX", "Europe volatility (VSTOXX)"),
        vol_metric("EM_VIX", "Emerging-market volatility (VXEEM)"),
        metric("ACWI drawdown", dd_now, f"{dd_now:.1f}%" if dd_now is not None else "—", "Distance from the running ACWI high.", dd)
    ]

    valuation = []
    cape_hist = pd.Series(dtype=float)
    if cape is not None:
        valuation.append(metric("US CAPE", cape, f"{cape:.1f}", f"Source: {cape_source}", pd.Series([cape], dtype=float)))
    else:
        valuation.append(metric("US CAPE", None, "Unavailable", "CAPE is updated slowly and should not be used as a short-term timing signal.", cape_hist))

    gold = raw["GOLD"]
    gold_now = float(gold.iloc[-1]) if len(gold) else None
    us10 = raw["US10Y"]
    us10_now = float(us10.iloc[-1]) if len(us10) else None
    cross_asset = [
        metric("US 10Y yield", us10_now, f"{us10_now:.2f}%" if us10_now is not None else "—", "Treasury market yield proxy.", us10),
        metric("Gold", gold_now, f"${gold_now:,.0f}" if gold_now is not None else "—", "Gold futures price proxy.", gold)
    ]

    # What is actually reflected in market prices. These are signals, not forecasts.
    vix = float(raw["VIX"].iloc[-1]) if len(raw["VIX"]) else None
    vstoxx = float(raw["VSTOXX"].iloc[-1]) if len(raw["VSTOXX"]) else None
    emvix = float(raw["EM_VIX"].iloc[-1]) if len(raw["EM_VIX"]) else None
    priced_in = [
        {"name":"Equity volatility already priced","display":f"VIX {vix:.1f}" if vix is not None else "Unavailable","explanation":"S&P 500 option prices imply this 30-day volatility level. VSTOXX and EM volatility beside it show whether the same risk pricing is concentrated in a region."},
        {"name":"Inflation priced into bonds","display":f"10Y breakeven {inflation:.1f}%" if inflation is not None else "Unavailable","explanation":"The 10-year inflation breakeven is the market-price difference between a nominal Treasury and an inflation-protected Treasury of similar maturity."},
        {"name":"Equity valuation being paid","display":f"CAPE {cape:.1f}" if cape is not None else "Unavailable","explanation":"A high valuation means investors are already paying a high price for current and long-term earnings. It is context, not a timing signal."}
    ]

    brief = market_brief(trends["ACWI"]["current"] if trends["ACWI"] else None, dd_now, vix, vstoxx, emvix)
    rules = rules_placeholder()
    latest = {
        "version":"2.0.0","mode":"LIVE","updated_at":now.strftime("%Y-%m-%d %H:%M UTC"),"data_through":max([raw[k].index[-1].strftime('%Y-%m-%d') for k in raw if len(raw[k])]),
        "brief":brief,"equities":equities,"risk":risk,"valuation":valuation,"cross_asset":cross_asset,
        "priced_in":priced_in,"rules":rules,
        "sources":["Yahoo Finance / yfinance","Cboe volatility indices","STOXX VSTOXX","FRED / U.S. Treasury inflation breakeven","Robert Shiller / Yale CAPE"]
    }

    # Compact history: weekly observations, up to ten years.
    weekly = raw["ACWI"].resample("W-FRI").last().dropna()
    history = {"dates":[d.strftime("%Y-%m-%d") for d in weekly.index],"acwi":[clean(v,2) for v in weekly.values]}
    (ROOT / OUTPUT_FILE).write_text(json.dumps(latest, indent=2), encoding="utf-8")
    (ROOT / HISTORY_FILE).write_text(json.dumps(history, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE} and {HISTORY_FILE}")


if __name__ == "__main__":
    main()

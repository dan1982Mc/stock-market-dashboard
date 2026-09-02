"""Build current V2 market JSON from free public market data."""
from datetime import datetime, timezone
from pathlib import Path
import json
import math
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
    try:
        raw = pd.read_csv(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}")
        raw["DATE"] = pd.to_datetime(raw["DATE"])
        raw[series_id] = pd.to_numeric(raw[series_id], errors="coerce")
        raw = raw.dropna(subset=[series_id])
        if raw.empty:
            return None, None, pd.Series(dtype=float)
        series = raw.set_index("DATE")[series_id]
        return float(series.iloc[-1]), series.index[-1].strftime("%Y-%m-%d"), series
    except Exception as exc:
        print(f"FRED {series_id} unavailable: {exc}")
        return None, None, pd.Series(dtype=float)


def load_cape():
    url = "https://www.econ.yale.edu/~shiller/data/ie_data.xls"
    try:
        df = pd.read_excel(url, sheet_name="Data", skiprows=7)
        candidates = [c for c in df.columns if "CAPE" in str(c).upper() or "P/E10" in str(c).upper()]
        if candidates:
            s = pd.to_numeric(df[candidates[0]], errors="coerce").dropna()
            if not s.empty:
                return float(s.iloc[-1]), s, "Robert Shiller / Yale"
    except Exception as exc:
        print(f"Automatic CAPE unavailable: {exc}")
    try:
        obj = json.loads((ROOT / CAPE_FILE).read_text(encoding="utf-8"))
        v = obj.get("us")
        return v, pd.Series([v], dtype=float) if v is not None else pd.Series(dtype=float), obj.get("source", {}).get("us", "Manual CAPE file")
    except Exception:
        return None, pd.Series(dtype=float), "Unavailable"


def safe_range(series):
    s = series.dropna()
    return band(s) if len(s) >= 20 else None


def metric(name, current, display, detail, hist_series, decimals=2):
    pct = percentile(current, hist_series) if current is not None else None
    return {"name":name,"current":clean(current,decimals),"display":display,"detail":detail,"percentile":pct,"percentile_label":f"P{int(pct)}" if pct is not None else None,"band":safe_range(hist_series) if current is not None else None}


def main():
    now = datetime.now(timezone.utc)
    raw = {key: series_for(ticker) for key,ticker in TICKERS.items()}
    if not raw["US10Y"].empty:
        raw["US10Y"] = raw["US10Y"] / 10.0

    trends = {key: trend_metrics(raw[key], MA_SHORT, MA_LONG) for key in ("ACWI","US","Europe","EM")}
    trend_history = {key: (raw[key] / raw[key].rolling(MA_LONG).mean() - 1) * 100 for key in ("ACWI","US","Europe","EM")}
    dd = drawdown_series(raw["ACWI"])
    dd_now = current_drawdown(raw["ACWI"])
    cape, cape_hist, cape_source = load_cape()
    inflation, inflation_date, inflation_hist = fred_latest(FRED_INFLATION)

    equities=[]
    for key,label in (("ACWI","ACWI"),("US","US equities"),("Europe","Europe"),("EM","Emerging markets")):
        t=trends[key]
        equities.append(metric(label,t["current"] if t else None,f"{t['current']:+.1f}% vs 200DMA" if t else "—",f"50DMA {t['ma50']:.1f} · 200DMA {t['ma200']:.1f}" if t else "Insufficient history",trend_history[key],1))

    def vol_metric(key,label):
        s=raw[key]; v=float(s.iloc[-1]) if len(s) else None
        return metric(label,v,f"{v:.1f}" if v is not None else "—","Current option-implied volatility index.",s,1)

    risk=[vol_metric("VIX","US volatility (VIX)"),vol_metric("VSTOXX","Europe volatility (VSTOXX)"),vol_metric("EM_VIX","Emerging-market volatility (VXEEM)"),metric("ACWI drawdown",dd_now,f"{dd_now:.1f}%" if dd_now is not None else "—","Distance from the running ACWI high.",dd,1)]
    valuation=[metric("US CAPE",cape,f"{cape:.1f}" if cape is not None else "Unavailable",f"Source: {cape_source}",cape_hist,1)]
    us10=raw["US10Y"]; us10_now=float(us10.iloc[-1]) if len(us10) else None
    gold=raw["GOLD"]; gold_now=float(gold.iloc[-1]) if len(gold) else None
    cross_asset=[metric("US 10Y yield",us10_now,f"{us10_now:.2f}%" if us10_now is not None else "—","Treasury market yield proxy.",us10,2),metric("Gold",gold_now,f"${gold_now:,.0f}" if gold_now is not None else "—","Gold futures price proxy.",gold,0)]

    vix=float(raw["VIX"].iloc[-1]) if len(raw["VIX"]) else None
    priced_in=[
        {"name":"Equity volatility already priced","display":f"US {vix:.1f}% implied" if vix is not None else "Unavailable","explanation":"Option prices embed near-term volatility. VSTOXX and VXEEM provide European and emerging-market context."},
        {"name":"Inflation priced into bonds","display":f"10Y breakeven {inflation:.1f}%" if inflation is not None else "Unavailable","explanation":"Nominal Treasury yield minus the comparable inflation-protected Treasury yield is a market-implied inflation measure."},
        {"name":"Equity valuation being paid","display":f"CAPE {cape:.1f}" if cape is not None else "Unavailable","explanation":"Valuation shows how much investors are paying for long-term earnings. Higher valuation means more optimism is already embedded in price."}
    ]

    brief=market_brief(trends["ACWI"]["current"] if trends["ACWI"] else None,dd_now,vix,float(raw["VSTOXX"].iloc[-1]) if len(raw["VSTOXX"]) else None,float(raw["EM_VIX"].iloc[-1]) if len(raw["EM_VIX"]) else None)
    latest={"version":"2.0.0","mode":"LIVE","updated_at":now.strftime("%Y-%m-%d %H:%M UTC"),"data_through":max(raw[k].index[-1].strftime('%Y-%m-%d') for k in raw if len(raw[k])),"brief":brief,"equities":equities,"risk":risk,"valuation":valuation,"cross_asset":cross_asset,"priced_in":priced_in,"rules":rules_placeholder(),"sources":["Yahoo Finance / yfinance","Cboe volatility indices","STOXX VSTOXX","FRED inflation breakeven","Robert Shiller / Yale CAPE"]}
    weekly=raw["ACWI"].resample("W-FRI").last().dropna()
    history={"dates":[d.strftime("%Y-%m-%d") for d in weekly.index],"acwi":[clean(v,2) for v in weekly.values]}
    (ROOT/OUTPUT_FILE).write_text(json.dumps(latest,indent=2),encoding="utf-8")
    (ROOT/HISTORY_FILE).write_text(json.dumps(history,indent=2),encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE} and {HISTORY_FILE}")

if __name__ == "__main__": main()

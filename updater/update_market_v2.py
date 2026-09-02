"""Build current V2 market JSON from free public market data."""
from datetime import datetime, timezone
from pathlib import Path
import io, json, requests
import pandas as pd
import yfinance as yf
from config import TICKERS,HISTORY_PERIOD,MA_LONG,MA_SHORT,OUTPUT_FILE,HISTORY_FILE,CAPE_FILE,FRED_INFLATION
from indicators import band,clean,trend_metrics,drawdown_series,current_drawdown,percentile
from scoring_v2 import market_brief,rules_placeholder
ROOT=Path(__file__).resolve().parents[1]
HEADERS={"User-Agent":"Mozilla/5.0 stock-market-dashboard/2.0"}

def series_for(ticker):
    try:
        df=yf.download(ticker,period=HISTORY_PERIOD,interval="1d",auto_adjust=True,progress=False,threads=False)
        if df.empty:return pd.Series(dtype=float)
        close=df["Close"]
        if isinstance(close,pd.DataFrame):close=close.iloc[:,0]
        return pd.to_numeric(close,errors="coerce").dropna()
    except Exception as exc:
        print(f"Data error {ticker}: {exc}");return pd.Series(dtype=float)

def csv_series(url,date_col,value_col,sep=","):
    try:
        r=requests.get(url,headers=HEADERS,timeout=30);r.raise_for_status()
        df=pd.read_csv(io.StringIO(r.text),sep=sep)
        d=pd.to_datetime(df[date_col],errors="coerce");v=pd.to_numeric(df[value_col],errors="coerce")
        s=pd.Series(v.to_numpy(),index=d).dropna().sort_index();return s[~s.index.duplicated(keep="last")]
    except Exception as exc:
        print(f"CSV source unavailable {url}: {exc}");return pd.Series(dtype=float)

def vxeem_series():
    return csv_series("https://cdn.cboe.com/api/global/us_indices/daily_prices/VXEEM_History.csv","DATE","VXEEM")

def vstoxx_series():
    return csv_series("https://convextrade.com/metrics/vstoxx/data.csv","Date","Value")

def fred_latest(series_id):
    try:
        r=requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",headers=HEADERS,timeout=30);r.raise_for_status()
        raw=pd.read_csv(io.StringIO(r.text));raw["DATE"]=pd.to_datetime(raw["DATE"],errors="coerce");raw[series_id]=pd.to_numeric(raw[series_id],errors="coerce");raw=raw.dropna(subset=["DATE",series_id])
        s=raw.set_index("DATE")[series_id].sort_index();return (float(s.iloc[-1]),s.index[-1].strftime("%Y-%m-%d"),s) if len(s) else (None,None,pd.Series(dtype=float))
    except Exception as exc:
        print(f"FRED {series_id} unavailable: {exc}");return None,None,pd.Series(dtype=float)

def load_cape():
    try:
        html=requests.get("https://www.multpl.com/shiller-pe/table/by-month",headers=HEADERS,timeout=30).text
        for t in pd.read_html(html):
            cols={str(c).strip().lower():c for c in t.columns}
            if "date" in cols and "value" in cols:
                d=pd.to_datetime(t[cols["date"]],errors="coerce");v=pd.to_numeric(t[cols["value"]],errors="coerce")
                s=pd.Series(v.to_numpy(),index=d).dropna().sort_index();s=s[~s.index.duplicated(keep="last")]
                if len(s)>=20:return float(s.iloc[-1]),s,"Robert Shiller data via Multpl"
    except Exception as exc: print(f"Automatic CAPE unavailable: {exc}")
    try:
        obj=json.loads((ROOT/CAPE_FILE).read_text(encoding="utf-8"));v=obj.get("us")
        return v,pd.Series([v],dtype=float) if v is not None else pd.Series(dtype=float),obj.get("source",{}).get("us","Manual CAPE file")
    except Exception:return None,pd.Series(dtype=float),"Unavailable"

def metric(name,current,display,detail,hist_series,decimals=2):
    return {"name":name,"current":clean(current,decimals),"display":display,"detail":detail,"percentile":percentile(current,hist_series) if current is not None else None,"percentile_label":f"P{int(percentile(current,hist_series))}" if current is not None and percentile(current,hist_series) is not None else None,"band":band(hist_series.dropna()) if current is not None and len(hist_series.dropna())>=20 else None}

def main():
    now=datetime.now(timezone.utc)
    raw={k:series_for(v) for k,v in TICKERS.items() if k not in ("VSTOXX","EM_VIX")};raw["VSTOXX"]=vstoxx_series();raw["EM_VIX"]=vxeem_series()
    trends={k:trend_metrics(raw[k],MA_SHORT,MA_LONG) for k in ("ACWI","US","Europe","EM")};trend_history={k:(raw[k]/raw[k].rolling(MA_LONG).mean()-1)*100 for k in trends};dd=drawdown_series(raw["ACWI"]);dd_now=current_drawdown(raw["ACWI"]);cape,cape_hist,cape_source=load_cape();inflation,inflation_date,inflation_hist=fred_latest(FRED_INFLATION)
    equities=[]
    for k,l in (("ACWI","ACWI"),("US","US equities"),("Europe","Europe"),("EM","Emerging markets")):
        t=trends[k];equities.append(metric(l,t["current"] if t else None,f"{t['current']:+.1f}% vs 200DMA" if t else "—",f"50DMA {t['ma50']:.1f} · 200DMA {t['ma200']:.1f}" if t else "Insufficient history",trend_history[k],1))
    def vol(k,l):
        s=raw[k];v=float(s.iloc[-1]) if len(s) else None;return metric(l,v,f"{v:.1f}" if v is not None else "—","30-day option-implied volatility index." if v is not None else "Data source unavailable.",s,1)
    risk=[vol("VIX","US volatility (VIX)"),vol("VSTOXX","Europe volatility (VSTOXX)"),vol("EM_VIX","Emerging-market volatility (VXEEM)"),metric("ACWI drawdown",dd_now,f"{dd_now:.1f}%" if dd_now is not None else "—","Distance from the running ACWI high.",dd,1)]
    valuation=[metric("US CAPE",cape,f"{cape:.1f}" if cape is not None else "Unavailable",f"Source: {cape_source}",cape_hist,1)]
    us10=raw["US10Y"];u10=float(us10.iloc[-1]) if len(us10) else None;gold=raw["GOLD"];g=float(gold.iloc[-1]) if len(gold) else None
    cross=[metric("US 10Y yield",u10,f"{u10:.2f}%" if u10 is not None else "—","Treasury market yield proxy.",us10,2),metric("Gold",g,f"${g:,.0f}" if g is not None else "—","Gold futures price proxy.",gold,0)]
    vix=float(raw["VIX"].iloc[-1]) if len(raw["VIX"]) else None;vsto=float(raw["VSTOXX"].iloc[-1]) if len(raw["VSTOXX"]) else None;emv=float(raw["EM_VIX"].iloc[-1]) if len(raw["EM_VIX"]) else None
    priced=[{"name":"Equity volatility already priced","display":f"US {vix:.1f} VIX" if vix is not None else "Unavailable","explanation":"Option prices embed near-term volatility; European and emerging-market volatility are shown alongside it."},{"name":"Inflation priced into bonds","display":f"10Y breakeven {inflation:.2f}%" if inflation is not None else "Unavailable","explanation":"Derived from nominal and inflation-indexed Treasury yields; this is a market-implied inflation expectation."},{"name":"Equity valuation being paid","display":f"CAPE {cape:.1f}" if cape is not None else "Unavailable","explanation":"CAPE compares the S&P 500 price with ten years of inflation-adjusted earnings; a high reading means a high multiple is being paid."}]
    dates=[raw[k].index[-1] for k in raw if len(raw[k])];latest={"version":"2.0.1","mode":"LIVE","updated_at":now.strftime("%Y-%m-%d %H:%M UTC"),"data_through":max(dates).strftime("%Y-%m-%d") if dates else None,"brief":market_brief(trends["ACWI"]["current"] if trends["ACWI"] else None,dd_now,vix,vsto,emv),"equities":equities,"risk":risk,"valuation":valuation,"cross_asset":cross,"priced_in":priced,"rules":rules_placeholder(),"sources":["Yahoo Finance / yfinance","Cboe volatility indices","STOXX VSTOXX / Convex fallback","FRED 10Y inflation breakeven","Robert Shiller data via Multpl"]}
    weekly=raw["ACWI"].resample("W-FRI").last().dropna();history={"dates":[d.strftime("%Y-%m-%d") for d in weekly.index],"acwi":[clean(v,2) for v in weekly.values]}
    (ROOT/OUTPUT_FILE).write_text(json.dumps(latest,indent=2),encoding="utf-8");(ROOT/HISTORY_FILE).write_text(json.dumps(history,indent=2),encoding="utf-8");print(f"Wrote {OUTPUT_FILE} and {HISTORY_FILE}")
if __name__=="__main__":main()

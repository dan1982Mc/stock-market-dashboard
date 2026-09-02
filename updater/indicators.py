"""Pure indicator calculations for the V2 dashboard."""

import math
import numpy as np


def clean(value, decimals=2):
    try:
        value = float(value)
        if not math.isfinite(value):
            return None
        return round(value, decimals)
    except (TypeError, ValueError):
        return None


def trend_metrics(series, ma_short=50, ma_long=200):
    series = series.dropna()
    if len(series) < ma_long:
        return None
    price = float(series.iloc[-1])
    ma50 = float(series.rolling(ma_short).mean().iloc[-1])
    ma200 = float(series.rolling(ma_long).mean().iloc[-1])
    distance = (price / ma200 - 1) * 100
    return {"current":clean(distance,1),"ma50":clean(ma50),"ma200":clean(ma200),"price":clean(price)}


def drawdown_series(series):
    series = series.dropna()
    return (series / series.cummax() - 1) * 100 if len(series) else series


def current_drawdown(series):
    dd = drawdown_series(series)
    return clean(dd.iloc[-1],1) if len(dd) else None


def percentile(value, series):
    if value is None or series is None:
        return None
    values = np.asarray(series.dropna(),dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return None
    return clean(np.mean(values <= float(value))*100,0)


def band(series, decimals=2):
    values = np.asarray(series.dropna(),dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 20:
        return None
    p05,p25,p50,p75,p95=np.percentile(values,[5,25,50,75,95])
    return {"p05":clean(p05,decimals),"p25":clean(p25,decimals),"p50":clean(p50,decimals),"p75":clean(p75,decimals),"p95":clean(p95,decimals),"p05_label":clean(p05,decimals),"p95_label":clean(p95,decimals)}

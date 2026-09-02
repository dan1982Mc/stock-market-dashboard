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
    if series is None or len(series.dropna()) < ma_long:
        return None
    series = series.dropna()
    price = float(series.iloc[-1])
    ma50 = float(series.rolling(ma_short).mean().iloc[-1])
    ma200 = float(series.rolling(ma_long).mean().iloc[-1])
    distance = (price / ma200 - 1) * 100
    return {"current": clean(distance, 1), "ma50": clean(ma50), "ma200": clean(ma200), "price": clean(price)}


def drawdown_series(series):
    series = series.dropna()
    if len(series) == 0:
        return series
    return (series / series.cummax() - 1) * 100


def current_drawdown(series):
    dd = drawdown_series(series)
    return clean(dd.iloc[-1], 1) if len(dd) else None


def percentile(value, series):
    series = np.asarray(series.dropna(), dtype=float)
    series = series[np.isfinite(series)]
    if len(series) == 0 or value is None:
        return None
    return clean((np.sum(series <= value) / len(series)) * 100, 0)


def band(series, current=None, decimals=2):
    series = np.asarray(series.dropna(), dtype=float)
    series = series[np.isfinite(series)]
    if len(series) < 20:
        return None
    current = float(series[-1] if current is None else current)
    qs = np.percentile(series, [5, 25, 50, 75, 95])
    pct = percentile(current, type("S", (), {"dropna": lambda self: series})())
    return {
        "p05": clean(qs[0], decimals), "p25": clean(qs[1], decimals),
        "p50": clean(qs[2], decimals), "p75": clean(qs[3], decimals), "p95": clean(qs[4], decimals),
        "p05_label": clean(qs[0], decimals), "p95_label": clean(qs[4], decimals),
        "percentile": pct
    }


def simple_status(current, warning=None, major=None, higher_is_bad=False):
    if current is None:
        return "NO DATA"
    if warning is None or major is None:
        return "WATCH"
    if higher_is_bad:
        if current >= major: return "MAJOR RISK"
        if current >= warning: return "WARNING"
        return "NORMAL"
    if current <= major: return "MAJOR RISK"
    if current <= warning: return "WARNING"
    return "NORMAL"

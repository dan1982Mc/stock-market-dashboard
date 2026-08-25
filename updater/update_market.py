"""
Global Stock Market Dashboard
V1.1 - Live market data updater

Downloads market data, calculates indicators and writes:

    data/latest.json

The frontend never talks directly to Yahoo Finance.
It only reads latest.json.

That separation is intentional.
"""

from pathlib import Path
from datetime import datetime, timezone

import json
import math

import numpy as np
import pandas as pd
import yfinance as yf

from config import (
    TICKERS,
    TREND_MA_SHORT,
    TREND_MA_LONG,
    DRAWDOWN_WARNING,
    DRAWDOWN_STRESS,
    VIX_CALM,
    VIX_NORMAL,
    VIX_ELEVATED,
    VIX_PANIC,
    VSTOXX_CALM,
    VSTOXX_NORMAL,
    VSTOXX_ELEVATED,
    VSTOXX_PANIC,
    OUTPUT_FILE,
    HISTORY_PERIOD,
)


# =========================================================
# HELPERS
# =========================================================

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / OUTPUT_FILE


def clean_number(value, decimals=2):
    """Convert numpy/pandas numbers to JSON-safe numbers."""

    if value is None:
        return None

    try:
        value = float(value)

        if math.isnan(value) or math.isinf(value):
            return None

        return round(value, decimals)

    except Exception:
        return None


def pct(value, decimals=1):
    value = clean_number(value, decimals)

    if value is None:
        return None

    return value


def safe_last(series):
    if series is None or len(series) == 0:
        return None

    series = series.dropna()

    if len(series) == 0:
        return None

    return float(series.iloc[-1])


def classify(
    value,
    green_max=None,
    yellow_max=None,
    orange_max=None,
):
    """
    Generic four-level classification.
    """

    if value is None:
        return {
            "status": "NO DATA",
            "emoji": "⚪",
            "class": "gray",
        }

    if green_max is not None and value <= green_max:
        return {
            "status": "CALM",
            "emoji": "🟢",
            "class": "green",
        }

    if yellow_max is not None and value <= yellow_max:
        return {
            "status": "NORMAL",
            "emoji": "🟡",
            "class": "yellow",
        }

    if orange_max is not None and value <= orange_max:
        return {
            "status": "ELEVATED",
            "emoji": "🟠",
            "class": "orange",
        }

    return {
        "status": "STRESS",
        "emoji": "🔴",
        "class": "red",
    }


# =========================================================
# DOWNLOAD
# =========================================================

def download_data():

    symbols = list(TICKERS.values())

    print("Downloading market data...")
    print(symbols)

    data = yf.download(
        symbols,
        period=HISTORY_PERIOD,
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,
    )

    return data


def get_close(data, ticker):

    try:

        if ticker not in data.columns.get_level_values(0):
            return pd.Series(dtype=float)

        series = data[ticker]["Close"].dropna()

        return series

    except Exception:

        return pd.Series(dtype=float)


# =========================================================
# TREND
# =========================================================

def calculate_trend(series):

    if len(series) < TREND_MA_LONG:
        return {
            "value": None,
            "ma50": None,
            "ma200": None,
            "signal": "INSUFFICIENT DATA",
        }

    price = safe_last(series)

    ma50 = series.rolling(TREND_MA_SHORT).mean().iloc[-1]
    ma200 = series.rolling(TREND_MA_LONG).mean().iloc[-1]

    if price > ma200 and ma50 > ma200:
        signal = "BULLISH"

    elif price > ma200:
        signal = "POSITIVE"

    elif price < ma200 and ma50 < ma200:
        signal = "BEARISH"

    else:
        signal = "MIXED"

    return {
        "value": clean_number(price),
        "ma50": clean_number(ma50),
        "ma200": clean_number(ma200),
        "signal": signal,
    }


# =========================================================
# DRAWDOWN
# =========================================================

def calculate_drawdown(series):

    if len(series) == 0:
        return None

    running_max = series.cummax()

    drawdown = (series / running_max - 1) * 100

    return clean_number(drawdown.iloc[-1])


# =========================================================
# RETURN
# =========================================================

def weekly_return(series):

    if len(series) < 6:
        return None

    current = series.iloc[-1]
    previous = series.iloc[-6]

    return clean_number((current / previous - 1) * 100)


# =========================================================
# VOLATILITY
# =========================================================

def build_volatility_indicator(
    name,
    value,
    calm,
    normal,
    elevated,
    panic,
):

    if value is None:

        return {
            "name": name,
            "status": "NO DATA",
            "emoji": "⚪",
            "class": "gray",
            "value": "—",
            "detail": "Data unavailable."
        }

    if value < calm:
        status = "CALM"
        emoji = "🟢"
        css = "green"

    elif value < normal:
        status = "NORMAL"
        emoji = "🟢"
        css = "green"

    elif value < elevated:
        status = "ELEVATED"
        emoji = "🟠"
        css = "orange"

    elif value < panic:
        status = "HIGH"
        emoji = "🔴"
        css = "red"

    else:
        status = "PANIC"
        emoji = "🔴"
        css = "red"

    return {
        "name": name,
        "status": status,
        "emoji": emoji,
        "class": css,
        "value": f"{value:.1f}",
        "detail": f"{name} current reading."
    }


# =========================================================
# CAPE
# =========================================================

def load_shiller_cape():

    """
    Attempts to retrieve the latest US CAPE from the
    Shiller data workbook.

    If unavailable, returns None rather than breaking
    the entire market update.
    """

    url = (
        "https://www.econ.yale.edu/~shiller/"
        "data/ie_data.xls"
    )

    try:

        df = pd.read_excel(
            url,
            sheet_name="Data",
            skiprows=7,
        )

        # Search columns for CAPE.
        possible = [
            c for c in df.columns
            if "CAPE" in str(c).upper()
            or "P/E10" in str(c).upper()
        ]

        if not possible:
            return None

        column = possible[0]

        series = pd.to_numeric(
            df[column],
            errors="coerce"
        ).dropna()

        if len(series) == 0:
            return None

        return clean_number(series.iloc[-1], 1)

    except Exception as exc:

        print("CAPE unavailable:", exc)

        return None


# =========================================================
# SCORE
# =========================================================

def calculate_score(
    trend_signal,
    vix,
    vstoxx,
    drawdown,
    cape,
):

    score = 50

    breakdown = {}

    # ---------------------------------------------
    # Trend
    # ---------------------------------------------

    if trend_signal == "BULLISH":
        score += 18
        breakdown["Trend"] = 18

    elif trend_signal == "POSITIVE":
        score += 10
        breakdown["Trend"] = 10

    elif trend_signal == "MIXED":
        score += 0
        breakdown["Trend"] = 10

    elif trend_signal == "BEARISH":
        score -= 18
        breakdown["Trend"] = 2

    else:
        breakdown["Trend"] = 10


    # ---------------------------------------------
    # VIX
    # ---------------------------------------------

    if vix is not None:

        if vix < VIX_NORMAL:
            score += 10
            breakdown["Volatility"] = 10

        elif vix < VIX_ELEVATED:
            score += 3
            breakdown["Volatility"] = 6

        else:
            score -= 12
            breakdown["Volatility"] = 1

    else:
        breakdown["Volatility"] = 5


    # ---------------------------------------------
    # VSTOXX
    # ---------------------------------------------

    if vstoxx is not None:

        if vstoxx < VSTOXX_NORMAL:
            score += 5

        elif vstoxx >= VSTOXX_ELEVATED:
            score -= 8


    # ---------------------------------------------
    # Drawdown
    # ---------------------------------------------

    if drawdown is not None:

        if drawdown > DRAWDOWN_WARNING:
            score += 8
            breakdown["Drawdown"] = 8

        elif drawdown > DRAWDOWN_STRESS:
            score += 0
            breakdown["Drawdown"] = 5

        else:
            score -= 10
            breakdown["Drawdown"] = 1

    else:
        breakdown["Drawdown"] = 5


    # ---------------------------------------------
    # CAPE
    # ---------------------------------------------

    if cape is not None:

        if cape < 20:
            score += 8
            breakdown["Valuation"] = 8

        elif cape < 28:
            score += 3
            breakdown["Valuation"] = 5

        elif cape < 35:
            score -= 4
            breakdown["Valuation"] = 3

        else:
            score -= 10
            breakdown["Valuation"] = 0

    else:
        breakdown["Valuation"] = 5


    score = max(0, min(100, score))

    return score, breakdown


# =========================================================
# REGIME
# =========================================================

def determine_regime(score):

    if score >= 70:

        return {
            "label": "BULLISH",
            "emoji": "🟢",
            "class": "green",
            "action": "MAINTAIN NORMAL INVESTING",
        }

    if score >= 50:

        return {
            "label": "NEUTRAL",
            "emoji": "🟡",
            "class": "yellow",
            "action": "CONTINUE NORMAL DCA",
        }

    if score >= 35:

        return {
            "label": "CAUTIOUS",
            "emoji": "🟠",
            "class": "orange",
            "action": "KEEP INVESTING — AVOID AGGRESSIVE BUYING",
        }

    return {
        "label": "STRESS",
        "emoji": "🔴",
        "class": "red",
        "action": "REDUCE RISK / REVIEW ALLOCATION",
    }


# =========================================================
# MAIN
# =========================================================

def main():

    now = datetime.now(timezone.utc)

    data = download_data()

    # -----------------------------------------------------
    # Series
    # -----------------------------------------------------

    acwi = get_close(data, TICKERS["ACWI"])
    europe = get_close(data, TICKERS["Europe"])
    em = get_close(data, TICKERS["EM"])
    sp500 = get_close(data, TICKERS["SP500"])

    vix_series = get_close(data, TICKERS["VIX"])
    vstoxx_series = get_close(data, TICKERS["VSTOXX"])
    us10y_series = get_close(data, TICKERS["US10Y"])

    # -----------------------------------------------------
    # Current values
    # -----------------------------------------------------

    vix = safe_last(vix_series)
    vstoxx = safe_last(vstoxx_series)
    us10y = safe_last(us10y_series)

    cape = load_shiller_cape()

    # -----------------------------------------------------
    # Trend
    # -----------------------------------------------------

    trend = calculate_trend(acwi)

    # -----------------------------------------------------
    # Drawdown
    # -----------------------------------------------------

    drawdown = calculate_drawdown(acwi)

    # -----------------------------------------------------
    # Weekly returns
    # -----------------------------------------------------

    acwi_week = weekly_return(acwi)
    europe_week = weekly_return(europe)
    em_week = weekly_return(em)

    # -----------------------------------------------------
    # Score
    # -----------------------------------------------------

    score, breakdown = calculate_score(
        trend["signal"],
        vix,
        vstoxx,
        drawdown,
        cape,
    )

    regime = determine_regime(score)

    reason = (
        f"Global trend is {trend['signal'].lower()}. "
        f"Volatility and valuation are incorporated into the score. "
        f"Current score: {score}/100."
    )

    # -----------------------------------------------------
    # Indicators
    # -----------------------------------------------------

    indicators = []

    # Trend
    trend_css = {
        "BULLISH": ("BULLISH", "🟢", "green"),
        "POSITIVE": ("POSITIVE", "🟢", "green"),
        "MIXED": ("MIXED", "🟡", "yellow"),
        "BEARISH": ("BEARISH", "🔴", "red"),
    }

    status, emoji, css = trend_css.get(
        trend["signal"],
        ("NO DATA", "⚪", "gray")
    )

    indicators.append({
        "name": "🌍 Global Trend",
        "status": status,
        "emoji": emoji,
        "class": css,
        "value": (
            f"ACWI {trend['value']:.2f}"
            if trend["value"] is not None
            else "—"
        ),
        "detail": (
            f"50DMA {trend['ma50']:.2f} · "
            f"200DMA {trend['ma200']:.2f}"
            if trend["ma50"] is not None
            else "Insufficient data."
        )
    })

    # Valuation
    if cape is None:

        valuation_status = "NO DATA"
        valuation_emoji = "⚪"
        valuation_class = "gray"
        valuation_value = "CAPE unavailable"

    elif cape < 20:

        valuation_status = "ATTRACTIVE"
        valuation_emoji = "🟢"
        valuation_class = "green"
        valuation_value = f"US CAPE {cape:.1f}"

    elif cape < 28:

        valuation_status = "NORMAL"
        valuation_emoji = "🟡"
        valuation_class = "yellow"
        valuation_value = f"US CAPE {cape:.1f}"

    elif cape < 35:

        valuation_status = "ELEVATED"
        valuation_emoji = "🟠"
        valuation_class = "orange"
        valuation_value = f"US CAPE {cape:.1f}"

    else:

        valuation_status = "EXPENSIVE"
        valuation_emoji = "🔴"
        valuation_class = "red"
        valuation_value = f"US CAPE {cape:.1f}"

    indicators.append({
        "name": "💰 Valuation",
        "status": valuation_status,
        "emoji": valuation_emoji,
        "class": valuation_class,
        "value": valuation_value,
        "detail": "US CAPE. Global valuation will be added in a later data-source upgrade."
    })

    # VIX
    indicators.append(
        build_volatility_indicator(
            "😨 US Volatility",
            clean_number(vix),
            VIX_CALM,
            VIX_NORMAL,
            VIX_ELEVATED,
            VIX_PANIC,
        )
    )

    # VSTOXX
    indicators.append(
        build_volatility_indicator(
            "🇪🇺 Europe Volatility",
            clean_number(vstoxx),
            VSTOXX_CALM,
            VSTOXX_NORMAL,
            VSTOXX_ELEVATED,
            VSTOXX_PANIC,
        )
    )

    # Drawdown
    if drawdown is None:

        dd_status = "NO DATA"
        dd_emoji = "⚪"
        dd_class = "gray"

    elif drawdown > DRAWDOWN_WARNING:

        dd_status = "NORMAL"
        dd_emoji = "🟢"
        dd_class = "green"

    elif drawdown > DRAWDOWN_STRESS:

        dd_status = "CORRECTION"
        dd_emoji = "🟠"
        dd_class = "orange"

    else:

        dd_status = "BEAR MARKET"
        dd_emoji = "🔴"
        dd_class = "red"

    indicators.append({
        "name": "📉 Global Drawdown",
        "status": dd_status,
        "emoji": dd_emoji,
        "class": dd_class,
        "value": f"{drawdown:.1f}%" if drawdown is not None else "—",
        "detail": "ACWI drawdown from its recent high."
    })

    # Rates
    indicators.append({
        "name": "💵 US 10Y Yield",
        "status": "MONITOR",
        "emoji": "🟡",
        "class": "yellow",
        "value": f"{us10y:.2f}%" if us10y is not None else "—",
        "detail": "Long-term interest rate proxy."
    })

    # -----------------------------------------------------
    # Snapshot
    # -----------------------------------------------------

    snapshot = [
        {
            "name": "ACWI",
            "value": f"{acwi_week:+.1f}%"
            if acwi_week is not None else "—"
        },
        {
            "name": "Europe",
            "value": f"{europe_week:+.1f}%"
            if europe_week is not None else "—"
        },
        {
            "name": "EM",
            "value": f"{em_week:+.1f}%"
            if em_week is not None else "—"
        },
        {
            "name": "VIX",
            "value": f"{vix:.1f}"
            if vix is not None else "—"
        },
        {
            "name": "VSTOXX",
            "value": f"{vstoxx:.1f}"
            if vstoxx is not None else "—"
        },
        {
            "name": "US10Y",
            "value": f"{us10y:.2f}%"
            if us10y is not None else "—"
        },
        {
            "name": "US CAPE",
            "value": f"{cape:.1f}"
            if cape is not None else "—"
        }
    ]

    # -----------------------------------------------------
    # Details
    # -----------------------------------------------------

    valuation_html = f"""
    <p>
        <strong>US CAPE:</strong>
        {cape:.1f}
        if cape is not None else "Unavailable"
    </p>
    <p>
        CAPE is a long-term valuation indicator.
        It should be used for expected-return context,
        not short-term market timing.
    </p>
    """

    risk_html = f"""
    <p>
        <strong>VIX:</strong>
        {vix:.1f}
        if vix is not None else "Unavailable"
    </p>
    <p>
        <strong>VSTOXX:</strong>
        {vstoxx:.1f}
        if vstoxx is not None else "Unavailable"
    </p>
    <p>
        <strong>ACWI drawdown:</strong>
        {drawdown:.1f}%
        if drawdown is not None else "Unavailable"
    </p>
    """

    # -----------------------------------------------------
    # Output
    # -----------------------------------------------------

    result = {

        "version": "1.1.0",

        "mode": "LIVE",

        "updated_at": now.strftime(
            "%Y-%m-%d %H:%M UTC"
        ),

        "data_through": (
            acwi.index[-1].strftime("%Y-%m-%d")
            if len(acwi)
            else None
        ),

        "overall": {
            "label": regime["label"],
            "emoji": regime["emoji"],
            "class": regime["class"],
            "score": score,
            "action": regime["action"],
            "reason": reason,
            "breakdown": breakdown,
        },

        "indicators": indicators,

        "snapshot": snapshot,

        "details": {
            "valuation": valuation_html,
            "risk": risk_html,
        },

        "what_matters": [
            f"Global trend: {trend['signal']}.",
            (
                f"US CAPE: {cape:.1f}."
                if cape is not None
                else "US CAPE unavailable."
            ),
            (
                f"VIX: {vix:.1f}."
                if vix is not None
                else "VIX unavailable."
            ),
            (
                f"ACWI drawdown: {drawdown:.1f}%."
                if drawdown is not None
                else "ACWI drawdown unavailable."
            ),
        ],

        "watch": [
            "ACWI vs 200-day moving average",
            "US and European volatility",
            "Global drawdown",
            "US CAPE",
            "US 10-year yield",
        ],

        "history": {
            "acwi": [],
            "score": [],
        },

        "sources": (
            "Yahoo Finance via yfinance; "
            "Robert Shiller/Yale CAPE dataset."
        ),
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("===================================")
    print(" MARKET UPDATE COMPLETE")
    print("===================================")
    print(f"Score: {score}")
    print(f"Regime: {regime['label']}")
    print(f"ACWI: {trend['value']}")
    print(f"VIX: {vix}")
    print(f"VSTOXX: {vstoxx}")
    print(f"CAPE: {cape}")
    print(f"Output: {OUTPUT_PATH}")
    print("===================================")


if __name__ == "__main__":
    main()

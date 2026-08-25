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
# PATHS
# =========================================================

ROOT = Path(__file__).resolve().parents[1]

OUTPUT_PATH = ROOT / OUTPUT_FILE


# =========================================================
# HELPERS
# =========================================================

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
    """Return a clean percentage value."""

    value = clean_number(value, decimals)

    if value is None:
        return None

    return value


def safe_last(series):
    """Return the latest valid value from a pandas Series."""

    if series is None or len(series) == 0:
        return None

    series = series.dropna()

    if len(series) == 0:
        return None

    return float(series.iloc[-1])


# =========================================================
# DOWNLOAD MARKET DATA
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

    ma50 = (
        series
        .rolling(TREND_MA_SHORT)
        .mean()
        .iloc[-1]
    )

    ma200 = (
        series
        .rolling(TREND_MA_LONG)
        .mean()
        .iloc[-1]
    )

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

    drawdown = (
        series / running_max - 1
    ) * 100

    return clean_number(
        drawdown.iloc[-1]
    )


# =========================================================
# WEEKLY RETURN
# =========================================================

def weekly_return(series):

    if len(series) < 6:
        return None

    current = series.iloc[-1]

    previous = series.iloc[-6]

    return clean_number(
        (current / previous - 1) * 100
    )


# =========================================================
# VOLATILITY INDICATOR
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
    Attempt to retrieve the latest US CAPE
    from the Shiller/Yale dataset.

    If unavailable, return None instead of
    breaking the entire dashboard update.
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

        possible = [
            c
            for c in df.columns
            if (
                "CAPE" in str(c).upper()
                or "P/E10" in str(c).upper()
            )
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

        return clean_number(
            series.iloc[-1],
            1
        )

    except Exception as exc:

        print(
            "CAPE unavailable:",
            exc
        )

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

    # -----------------------------------------------------
    # TREND
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # VIX
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # VSTOXX
    # -----------------------------------------------------

    if vstoxx is not None:

        if vstoxx < VSTOXX_NORMAL:

            score += 5

        elif vstoxx >= VSTOXX_ELEVATED:

            score -= 8


    # -----------------------------------------------------
    # DRAWDOWN
    # -----------------------------------------------------

    if drawdown is not None:

        if drawdown > DRAWDOWN_WARNING:

            score += 8
            breakdown["Drawdown"] = 8

        elif drawdown > DRAWDOWN_STRESS:

            breakdown["Drawdown"] = 5

        else:

            score -= 10
            breakdown["Drawdown"] = 1

    else:

        breakdown["Drawdown"] = 5


    # -----------------------------------------------------
    # CAPE
    # -----------------------------------------------------

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


    score = max(
        0,
        min(100, score)
    )

    return score, breakdown


# =========================================================
# MARKET REGIME
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
            "action": (
                "KEEP INVESTING — "
                "AVOID AGGRESSIVE BUYING"
            ),
        }

    return {
        "label": "STRESS",
        "emoji": "🔴",
        "class": "red",
        "action": (
            "REDUCE RISK / "
            "REVIEW ALLOCATION"
        ),
    }


# =========================================================
# MAIN
# =========================================================

def main():

    now = datetime.now(
        timezone.utc
    )

    # -----------------------------------------------------
    # DOWNLOAD
    # -----------------------------------------------------

    data = download_data()

    # -----------------------------------------------------
    # MARKET SERIES
    # -----------------------------------------------------

    acwi = get_close(
        data,
        TICKERS["ACWI"]
    )

    europe = get_close(
        data,
        TICKERS["Europe"]
    )

    em = get_close(
        data,
        TICKERS["EM"]
    )

    sp500 = get_close(
        data,
        TICKERS["SP500"]
    )

    vix_series = get_close(
        data,
        TICKERS["VIX"]
    )

    vstoxx_series = get_close(
        data,
        TICKERS["VSTOXX"]
    )

    us10y_series = get_close(
        data,
        TICKERS["US10Y"]
    )

    # -----------------------------------------------------
    # CURRENT VALUES
    # -----------------------------------------------------

    vix = safe_last(
        vix_series
    )

    vstoxx = safe_last(
        vstoxx_series
    )

    us10y = safe_last(
        us10y_series
    )

    cape = load_shiller_cape()

    # -----------------------------------------------------
    # TREND
    # -----------------------------------------------------

    trend = calculate_trend(
        acwi
    )

    # -----------------------------------------------------
    # DRAWDOWN
    # -----------------------------------------------------

    drawdown = calculate_drawdown(
        acwi
    )

    # -----------------------------------------------------
    # WEEKLY RETURNS
    # -----------------------------------------------------

    acwi_week = weekly_return(
        acwi
    )

    europe_week = weekly_return(
        europe
    )

    em_week = weekly_return(
        em
    )

    # -----------------------------------------------------
    # SCORE
    # -----------------------------------------------------

    score, breakdown = calculate_score(
        trend["signal"],
        vix,
        vstoxx,
        drawdown,
        cape,
    )

    regime = determine_regime(
        score
    )

    reason = (
        f"Global trend is "
        f"{trend['signal'].lower()}. "
        f"Volatility and valuation are "
        f"incorporated into the score. "
        f"Current score: {score}/100."
    )

    # =====================================================
    # INDICATORS
    # =====================================================

    indicators = []

    # -----------------------------------------------------
    # GLOBAL TREND
    # -----------------------------------------------------

    trend_css = {

        "BULLISH": (
            "BULLISH",
            "🟢",
            "green"
        ),

        "POSITIVE": (
            "POSITIVE",
            "🟢",
            "green"
        ),

        "MIXED": (
            "MIXED",
            "🟡",
            "yellow"
        ),

        "BEARISH": (
            "BEARISH",
            "🔴",
            "red"
        ),
    }

    (
        status,
        emoji,
        css
    ) = trend_css.get(
        trend["signal"],
        (
            "NO DATA",
            "⚪",
            "gray"
        )
    )

    if trend["value"] is not None:

        trend_value = (
            f"ACWI {trend['value']:.2f}"
        )

    else:

        trend_value = "—"

    if (
        trend["ma50"] is not None
        and trend["ma200"] is not None
    ):

        trend_detail = (
            f"50DMA {trend['ma50']:.2f} · "
            f"200DMA {trend['ma200']:.2f}"
        )

    else:

        trend_detail = (
            "Insufficient data."
        )

    indicators.append({

        "name": "🌍 Global Trend",

        "status": status,

        "emoji": emoji,

        "class": css,

        "value": trend_value,

        "detail": trend_detail,

    })

    # -----------------------------------------------------
    # VALUATION
    # -----------------------------------------------------

    if cape is None:

        valuation_status = "NO DATA"

        valuation_emoji = "⚪"

        valuation_class = "gray"

        valuation_value = (
            "CAPE unavailable"
        )

    elif cape < 20:

        valuation_status = "ATTRACTIVE"

        valuation_emoji = "🟢"

        valuation_class = "green"

        valuation_value = (
            f"US CAPE {cape:.1f}"
        )

    elif cape < 28:

        valuation_status = "NORMAL"

        valuation_emoji = "🟡"

        valuation_class = "yellow"

        valuation_value = (
            f"US CAPE {cape:.1f}"
        )

    elif cape < 35:

        valuation_status = "ELEVATED"

        valuation_emoji = "🟠"

        valuation_class = "orange"

        valuation_value = (
            f"US CAPE {cape:.1f}"
        )

    else:

        valuation_status = "EXPENSIVE"

        valuation_emoji = "🔴"

        valuation_class = "red"

        valuation_value = (
            f"US CAPE {cape:.1f}"
        )

    indicators.append({

        "name": "💰 Valuation",

        "status": valuation_status,

        "emoji": valuation_emoji,

        "class": valuation_class,

        "value": valuation_value,

        "detail": (
            "US CAPE. Global valuation will "
            "be added in a later data-source "
            "upgrade."
        ),

    })

    # -----------------------------------------------------
    # US VOLATILITY
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # EUROPE VOLATILITY
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # DRAWDOWN
    # -----------------------------------------------------

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

        "value": (
            f"{drawdown:.1f}%"
            if drawdown is not None
            else "—"
        ),

        "detail": (
            "ACWI drawdown from "
            "its recent high."
        ),

    })

    # -----------------------------------------------------
    # US 10Y
    # -----------------------------------------------------

    indicators.append({

        "name": "💵 US 10Y Yield",

        "status": "MONITOR",

        "emoji": "🟡",

        "class": "yellow",

        "value": (
            f"{us10y:.2f}%"
            if us10y is not None
            else "—"
        ),

        "detail": (
            "Long-term interest "
            "rate proxy."
        ),

    })

    # =====================================================
    # SNAPSHOT
    # =====================================================

    snapshot = [

        {
            "name": "ACWI",
            "value": (
                f"{acwi_week:+.1f}%"
                if acwi_week is not None
                else "—"
            ),
        },

        {
            "name": "Europe",
            "value": (
                f"{europe_week:+.1f}%"
                if europe_week is not None
                else "—"
            ),
        },

        {
            "name": "EM",
            "value": (
                f"{em_week:+.1f}%"
                if em_week is not None
                else "—"
            ),
        },

        {
            "name": "VIX",
            "value": (
                f"{vix:.1f}"
                if vix is not None
                else "—"
            ),
        },

        {
            "name": "VSTOXX",
            "value": (
                f"{vstoxx:.1f}"
                if vstoxx is not None
                else "—"
            ),
        },

        {
            "name": "US10Y",
            "value": (
                f"{us10y:.2f}%"
                if us10y is not None
                else "—"
            ),
        },

        {
            "name": "US CAPE",
            "value": (
                f"{cape:.1f}"
                if cape is not None
                else "—"
            ),
        },

    ]

    # =====================================================
    # CORRECTED TEXT BLOCK
    # =====================================================

    cape_text = (
        f"{cape:.1f}"
        if cape is not None
        else "Unavailable"
    )

    vix_text = (
        f"{vix:.1f}"
        if vix is not None
        else "Unavailable"
    )

    vstoxx_text = (
        f"{vstoxx:.1f}"
        if vstoxx is not None
        else "Unavailable"
    )

    drawdown_text = (
        f"{drawdown:.1f}%"
        if drawdown is not None
        else "Unavailable"
    )

    valuation_html = f"""
    <p>
        <strong>US CAPE:</strong> {cape_text}
    </p>

    <p>
        CAPE is a long-term valuation indicator.
        It should be used for expected-return context,
        not short-term market timing.
    </p>
    """

    risk_html = f"""
    <p>
        <strong>VIX:</strong> {vix_text}
    </p>

    <p>
        <strong>VSTOXX:</strong> {vstoxx_text}
    </p>

    <p>
        <strong>ACWI drawdown:</strong> {drawdown_text}
    </p>
    """

    # =====================================================
    # OUTPUT
    # =====================================================

    if len(acwi):

        data_through = (
            acwi.index[-1]
            .strftime("%Y-%m-%d")
        )

    else:

        data_through = None

    result = {

        "version": "1.1.0",

        "mode": "LIVE",

        "updated_at": now.strftime(
            "%Y-%m-%d %H:%M UTC"
        ),

        "data_through": data_through,

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

            "valuation":
                valuation_html,

            "risk":
                risk_html,

        },

        "what_matters": [

            f"Global trend: "
            f"{trend['signal']}.",

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
                f"ACWI drawdown: "
                f"{drawdown:.1f}%."
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

    # -----------------------------------------------------
    # WRITE JSON
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # TERMINAL SUMMARY
    # -----------------------------------------------------

    print()
    print("===================================")
    print(" MARKET UPDATE COMPLETE")
    print("===================================")
    print(
        f"Score: {score}"
    )
    print(
        f"Regime: {regime['label']}"
    )
    print(
        f"ACWI: {trend['value']}"
    )
    print(
        f"VIX: {vix}"
    )
    print(
        f"VSTOXX: {vstoxx}"
    )
    print(
        f"CAPE: {cape}"
    )
    print(
        f"Output: {OUTPUT_PATH}"
    )
    print("===================================")


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()

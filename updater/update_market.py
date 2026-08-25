"""
MAIN MARKET UPDATE

Responsibilities:

1. Download market data
2. Calculate indicators
3. Calculate score
4. Generate latest.json

It does NOT render HTML.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


from data_sources import (
    CONFIG,
    download_history,
    latest_value,
    latest_date,
    load_cape
)

from indicators import (
    trend_score,
    current_drawdown,
    breadth_proxy,
    volatility_status,
    drawdown_status,
    breadth_status,
    cape_status
)

from scoring import (
    calculate_score,
    market_regime
)


ROOT =
    Path(__file__).resolve().parents[1]


def pct_change(
    series,
    periods
):

    if len(series) <= periods:

        return None

    return (
        series.iloc[-1] /
        series.iloc[-periods] -
        1
    ) * 100


def load_all_market_data():

    history = {}

    benchmarks =
        CONFIG["benchmarks"]

    for key, info in benchmarks.items():

        print(
            f"Downloading {key}: "
            f"{info['ticker']}"
        )

        history[key] =
            download_history(
                info["ticker"],
                CONFIG["update"]
                ["price_history"]
            )


    volatility = {}

    for key, info in \
            CONFIG["volatility"].items():

        print(
            f"Downloading volatility: "
            f"{key}"
        )

        volatility[key] =
            download_history(
                info["ticker"],
                "1y"
            )


    rates = {}

    for key, info in \
            CONFIG["rates"].items():

        print(
            f"Downloading rate: {key}"
        )

        rates[key] =
            download_history(
                info["ticker"],
                "1y"
            )


    return (
        history,
        volatility,
        rates
    )


def main():

    (
        history,
        volatility,
        rates
    ) = load_all_market_data()


    cape =
        load_cape()


    global_market = history["global"]


    # ========================================================
    # RAW VALUES
    # ========================================================

    trend = trend_score(global_market)


    drawdown = current_drawdown(global_market)


    breadth = breadth_proxy(list(history.values()))


    vix = latest_value(volatility.get("us"))


    vstoxx = latest_value(volatility.get("europe"))


    eafe_vol = latest_value(volatility.get("developed_ex_us"))


    em_vol = latest_value(volatility.get("emerging"))


    us10 = latest_value(rates.get("us10y"))


    us3m =latest_value(rates.get("us3m"))


    # ========================================================
    # STATES
    # ========================================================

    if trend is None:

        trend_state = "UNAVAILABLE"

    elif trend >= 75:

        trend_state = "BULLISH"

    elif trend >= 45:

        trend_state = "NEUTRAL"

    else:

        trend_state = "BEARISH"


    valuation_state =
        cape_status(
            cape.get("global")
        )


    vol_state =
        volatility_status(
            vix
        )


    breadth_state =
        breadth_status(
            breadth
        )


    if us10 is None:

        rate_state = "UNAVAILABLE"

    elif us10 >= 4.5:

        rate_state = "RESTRICTIVE"

    elif us10 >= 4.0:

        rate_state = "CAUTION"

    else:

        rate_state = "NEUTRAL"


    drawdown_state =
        drawdown_status(
            drawdown
        )


    if vix is None:

        sentiment_state = "UNAVAILABLE"

    elif vix < 18:

        sentiment_state = "OPTIMISTIC"

    elif vix < 25:

        sentiment_state = "NEUTRAL"

    else:

        sentiment_state = "FEARFUL"


    states = {

        "trend":
            trend_state,

        "valuation":
            valuation_state,

        "volatility":
            vol_state,

        "breadth":
            breadth_state,

        "rates":
            rate_state,

        "drawdown":
            drawdown_state,

        "sentiment":
            sentiment_state
    }


    # ========================================================
    # SCORE
    # ========================================================

    weights =
        CONFIG["scoring"]
        ["weights"]


    score, breakdown =
        calculate_score(
            states,
            weights
        )


    regime =
        market_regime(
            score
        )


    # ========================================================
    # INDICATOR DATA
    # ========================================================

    indicator_data = [

        indicator(
            "🌍 Global trend",
            trend_state,
            f"{trend}/100"
            if trend is not None
            else "—",
            "ACWI trend score"
        ),


        indicator(
            "💰 Valuation",
            valuation_state,
            f"Global CAPE: "
            f"{cape.get('global')
              or '—'}",
            f"US CAPE: "
            f"{cape.get('us')
              or '—'}"
        ),


        indicator(
            "😨 Global volatility",
            vol_state,
            f"VIX: "
            f"{vix:.1f}"
            if vix is not None
            else "—",
            f"Europe: "
            f"{vstoxx:.1f}"
            if vstoxx is not None
            else "—"
        ),


        indicator(
            "📊 Global breadth",
            breadth_state,
            f"{breadth:.0f}%"
            if breadth is not None
            else "—",
            "Regional ETF proxy"
        ),


        indicator(
            "💵 Rates & liquidity",
            rate_state,
            f"US 10Y: "
            f"{us10:.2f}%"
            if us10 is not None
            else "—",
            f"US 3M: "
            f"{us3m:.2f}%"
            if us3m is not None
            else "—"
        ),


        indicator(
            "📉 Drawdown / stress",
            drawdown_state,
            f"{drawdown:.1f}%"
            if drawdown is not None
            else "—",
            "ACWI from recent high"
        ),


        indicator(
            "🧠 Sentiment",
            sentiment_state,
            f"VIX: "
            f"{vix:.1f}"
            if vix is not None
            else "—",
            "Low-weight confirmation"
        )

    ]


    # ========================================================
    # SNAPSHOT
    # ========================================================

    snapshot = []


    def add_snapshot(
        name,
        value
    ):

        snapshot.append({

            "name": name,

            "value":
                "—"
                if value is None
                else value
        })


    global_value =
        latest_value(
            global_market
        )


    add_snapshot(
        "ACWI",
        f"{global_value:.2f}"
        if global_value
        else None
    )


    one_year =
        pct_change(
            global_market,
            252
        )


    add_snapshot(
        "ACWI 1Y",
        f"{one_year:+.1f}%"
        if one_year is not None
        else None
    )


    add_snapshot(
        "VIX",
        f"{vix:.1f}"
        if vix is not None
        else None
    )


    add_snapshot(
        "VSTOXX",
        f"{vstoxx:.1f}"
        if vstoxx is not None
        else None
    )


    add_snapshot(
        "US 10Y",
        f"{us10:.2f}%"
        if us10 is not None
        else None
    )


    add_snapshot(
        "ACWI DD",
        f"{drawdown:.1f}%"
        if drawdown is not None
        else None
    )


    add_snapshot(
        "Global CAPE",
        cape.get("global")
    )


    add_snapshot(
        "US CAPE",
        cape.get("us")
    )


    # ========================================================
    # OUTPUT
    # ========================================================

    data = {

        "updated_at":
            datetime.now(
                timezone.utc
            ).astimezone()
            .strftime(
                "%Y-%m-%d %H:%M %Z"
            ),

        "data_through":
            latest_date(
                global_market
            ),


        "overall": {

            "label":
                regime["label"],

            "emoji":
                regime["emoji"],

            "class":
                regime["class"],

            "score":
                score,

            "action":
                regime["action"],

            "reason":
                build_reason(
                    states
                ),

            "breakdown":
                breakdown
        },


        "indicators":
            indicator_data,


        "snapshot":
            snapshot,


        "details": {

            "valuation":
                build_valuation_html(
                    cape
                ),

            "risk":
                build_risk_html(
                    vix,
                    vstoxx,
                    eafe_vol,
                    em_vol,
                    breadth,
                    drawdown
                )
        },


        "what_matters":
            build_what_matters(
                states
            ),


        "watch": [

            "ACWI vs 200DMA",

            "Global breadth",

            "VIX and regional volatility",

            "Long-term yields",

            "Next quarterly CAPE update"
        ],


        "history":
            build_history(
                global_market
            ),


        "sources":
            "Market prices: Yahoo Finance "
            "(via yfinance). "
            "CAPE: Shiller / Idea Farm. "
            "Volatility: Cboe / STOXX "
            "where available. "
            "Informational only; not investment advice."
    }


    output =
        ROOT /
        "data" /
        "latest.json"


    with open(
        output,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


    print(
        f"Dashboard updated: "
        f"{regime['label']} "
        f"{score}/100"
    )


def indicator(
    name,
    status,
    value,
    detail
):

    return {

        "name": name,

        "status": status,

        "emoji":
            status_emoji(
                status
            ),

        "class":
            status_class(
                status
            ),

        "value": value,

        "detail": detail,

        "as_of":
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d"
            ),

        "explanation":
            explanation(
                name
            )
    }


def status_emoji(status):

    if status in [
        "BULLISH",
        "HEALTHY",
        "ATTRACTIVE",
        "NORMAL"
    ]:

        return "🟢"


    if status in [
        "NEUTRAL",
        "MIXED",
        "ELEVATED",
        "OPTIMISTIC"
    ]:

        return "🟡"


    if status in [
        "EXPENSIVE",
        "RESTRICTIVE",
        "CAUTION"
    ]:

        return "🟠"


    return "🔴"


def status_class(status):

    return {

        "BULLISH": "green",
        "HEALTHY": "green",
        "ATTRACTIVE": "green",
        "NORMAL": "green",

        "NEUTRAL": "yellow",
        "MIXED": "yellow",
        "ELEVATED": "yellow",
        "OPTIMISTIC": "yellow",

        "EXPENSIVE": "orange",
        "RESTRICTIVE": "orange",
        "CAUTION": "orange",

        "BEARISH": "red",
        "WEAK": "red",
        "STRESS": "red",
        "PANIC": "red",
        "EXTREME": "red",

        "FEARFUL": "red"

    }.get(
        status,
        "yellow"
    )


def explanation(name):

    explanations = {

        "🌍 Global trend": {

            "what":
                "Measures global equity price trend using price versus the 50- and 200-day moving averages plus momentum.",

            "legend": [

                "🟢 Bullish: strong trend",

                "🟡 Neutral: mixed trend",

                "🔴 Bearish: deteriorating trend"
            ],

            "why":
                "A healthy trend generally supports remaining invested.",

            "source":
                "ACWI market-price history"
        },


        "💰 Valuation": {

            "what":
                "Measures how expensive equities are compared with long-term earnings and historical valuation ranges.",

            "legend": [

                "🟢 Attractive",

                "🟡 Normal",

                "🟠 Expensive",

                "🔴 Extreme"
            ],

            "why":
                "Valuation is mainly useful for estimating long-term expected returns, not short-term market timing.",

            "source":
                "Shiller / Idea Farm"
        },


        "😨 Global volatility": {

            "what":
                "Measures expected equity-market volatility. The dashboard separates US, Europe, developed ex-US and emerging-market measures where free data is available.",

            "legend": [

                "🟢 <20: normal",

                "🟡 20–30: elevated",

                "🟠 30–40: high stress",

                "🔴 >40: extreme"
            ],

            "why":
                "Sharp volatility increases often accompany market stress.",

            "source":
                "Cboe / STOXX"
        },


        "📊 Global breadth": {

            "what":
                "Percentage of selected regional benchmark markets above their 200-day moving average.",

            "legend": [

                "🟢 ≥80%: broad",

                "🟡 50–79%: mixed",

                "🔴 <50%: weak"
            ],

            "why":
                "A market advance supported by many regions is generally more robust.",

            "source":
                "Regional market-price proxies"
        },


        "💵 Rates & liquidity": {

            "what":
                "Tracks the interest-rate environment affecting equity valuations and financial conditions.",

            "legend": [

                "🟢 Supportive",

                "🟡 Neutral",

                "🟠 Restrictive",

                "🔴 Severe tightening"
            ],

            "why":
                "Higher yields can place pressure on equity valuations.",

            "source":
                "Treasury market"
        },


        "📉 Drawdown / stress": {

            "what":
                "Measures the percentage decline of global equities from their most recent peak.",

            "legend": [

                "🟢 0 to -5%: normal",

                "🟡 -5 to -10%: correction",

                "🟠 -10 to -20%: major correction",

                "🔴 below -20%: bear-market territory"
            ],

            "why":
                "Large drawdowns become more significant when combined with volatility and weak breadth.",

            "source":
                "ACWI market-price history"
        },


        "🧠 Sentiment": {

            "what":
                "A low-weight confirmation signal based mainly on market volatility.",

            "legend": [

                "🟢 Calm",

                "🟡 Neutral",

                "🔴 Fearful"
            ],

            "why":
                "Sentiment should confirm rather than dominate the market assessment.",

            "source":
                "Volatility / sentiment proxies"
        }
    }


    return explanations[name]


def build_reason(states):

    if states["drawdown"] in [
        "STRESS",
        "BEAR_MARKET"
    ]:

        return (
            "Global equities are under "
            "significant pressure. "
            "Check volatility and breadth "
            "before making major decisions."
        )


    if states["volatility"] in [
        "HIGH",
        "EXTREME"
    ]:

        return (
            "Volatility is elevated. "
            "Avoid reacting to a single "
            "market move."
        )


    if states["valuation"] in [
        "EXPENSIVE",
        "EXTREME"
    ]:

        return (
            "Valuations are elevated, "
            "but this alone is not a "
            "short-term sell signal."
        )


    return (
        "No single indicator currently "
        "shows a major global stress signal."
    )


def build_valuation_html(cape):

    return f"""
    <div class="detail-columns">

        <div class="detail-box">

            <h4>Global valuation</h4>

            <p>
                Global CAPE:
                <strong>
                    {cape.get("global") or "—"}
                </strong>
            </p>

            <p>
                Developed:
                <strong>
                    {cape.get("developed") or "—"}
                </strong>
            </p>

            <p>
                Emerging:
                <strong>
                    {cape.get("emerging") or "—"}
                </strong>
            </p>

        </div>


        <div class="detail-box">

            <h4>US valuation</h4>

            <p>
                US CAPE:
                <strong>
                    {cape.get("us") or "—"}
                </strong>
            </p>

            <p>
                CAPE is manually updated
                approximately quarterly.
            </p>

            <p>
                It is a long-term valuation
                indicator, not a timing signal.
            </p>

        </div>

    </div>
    """


def build_risk_html(
    vix,
    vstoxx,
    eafe,
    emerging,
    breadth,
    drawdown
):

    def fmt(value):

        if value is None:

            return "N/A"

        return f"{value:.1f}"


    return f"""
    <div class="detail-columns">

        <div class="detail-box">

            <h4>Regional volatility</h4>

            <p>
                US VIX:
                {fmt(vix)}
            </p>

            <p>
                Europe:
                {fmt(vstoxx)}
            </p>

            <p>
                Developed ex-US:
                {fmt(eafe)}
            </p>

            <p>
                Emerging:
                {fmt(emerging)}
            </p>

        </div>


        <div class="detail-box">

            <h4>Global stress</h4>

            <p>
                Breadth:
                {fmt(breadth)}%
            </p>

            <p>
                ACWI drawdown:
                {fmt(drawdown)}%
            </p>

            <p>
                Stress should be judged
                from several indicators,
                not volatility alone.
            </p>

        </div>

    </div>
    """


def build_what_matters(states):

    result = []


    if states["valuation"] in [
        "EXPENSIVE",
        "EXTREME"
    ]:

        result.append(
            "Valuation is elevated."
        )


    if states["trend"] == "BULLISH":

        result.append(
            "Global equity trend remains supportive."
        )


    if states["breadth"] != "HEALTHY":

        result.append(
            "Global breadth is not uniformly strong."
        )


    if states["volatility"] in [
        "HIGH",
        "EXTREME"
    ]:

        result.append(
            "Volatility is elevated."
        )


    if not result:

        result.append(
            "No major global warning signal is currently dominant."
        )


    return result


def build_history(series):

    if len(series) == 0:

        return None


    recent =
        series.tail(252)


    return {

        "labels":
            [
                x.strftime("%Y-%m-%d")
                for x in recent.index
            ],

        "values":
            [
                round(float(x), 2)
                for x in recent.values
            ]
    }


if __name__ == "__main__":

    main()
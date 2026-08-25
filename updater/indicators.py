"""
INDICATOR CALCULATIONS

This file calculates raw indicators.

It does NOT decide whether the market is
good or bad. That belongs in scoring.py.
"""

import numpy as np


def moving_average(
    series,
    days
):

    return series.rolling(
        days
    ).mean()


def trend_score(
    price,
    days_50=50,
    days_200=200
):

    if len(price) < days_200:

        return None


    ma50 =
        moving_average(
            price,
            days_50
        )

    ma200 =
        moving_average(
            price,
            days_200
        )


    current =
        float(price.iloc[-1])

    score = 0


    # Price above 200DMA

    if current > ma200.iloc[-1]:

        score += 50


    # 50DMA above 200DMA

    if ma50.iloc[-1] > ma200.iloc[-1]:

        score += 30


    # 3-month momentum

    if len(price) >= 64:

        if current > price.iloc[-64]:

            score += 20


    return score


def drawdown(series):

    peak =
        series.cummax()

    return (
        series / peak - 1
    ) * 100


def current_drawdown(series):

    dd =
        drawdown(series)

    if len(dd) == 0:

        return None

    return float(
        dd.iloc[-1]
    )


def breadth_proxy(
    regional_series
):

    """
    This is deliberately called a PROXY.

    It measures the percentage of selected
    regional benchmark ETFs above their
    200-day moving average.

    It is NOT true all-stock global breadth.
    """

    values = []


    for series in regional_series:

        if len(series) < 200:

            continue


        ma200 =
            series.rolling(
                200
            ).mean()


        values.append(
            series.iloc[-1]
            >
            ma200.iloc[-1]
        )


    if not values:

        return None


    return (
        sum(values)
        /
        len(values)
        *
        100
    )


def volatility_status(
    value
):

    if value is None:

        return "UNAVAILABLE"


    if value < 20:

        return "NORMAL"

    if value < 30:

        return "ELEVATED"

    if value < 40:

        return "HIGH"

    return "EXTREME"


def drawdown_status(
    value
):

    if value is None:

        return "UNAVAILABLE"


    if value > -5:

        return "NORMAL"

    if value > -10:

        return "CORRECTION"

    if value > -20:

        return "MAJOR_CORRECTION"

    return "BEAR_MARKET"


def breadth_status(
    value
):

    if value is None:

        return "UNAVAILABLE"


    if value >= 80:

        return "HEALTHY"

    if value >= 50:

        return "MIXED"

    return "WEAK"


def cape_status(
    value
):

    if value is None:

        return "UNAVAILABLE"


    if value < 15:

        return "ATTRACTIVE"

    if value < 22:

        return "NORMAL"

    if value < 30:

        return "EXPENSIVE"

    return "EXTREME"
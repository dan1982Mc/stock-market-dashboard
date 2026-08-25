"""
DATA SOURCES

All external market-data access should live in this file.

If we later replace Yahoo Finance with another provider,
the rest of the application should remain unchanged.
"""

from pathlib import Path
import json

import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]


def load_config():

    path = ROOT / "config" / "config.json"

    with open(path, "r", encoding="utf-8") as f:

        return json.load(f)


CONFIG = load_config()


def download_history(
    ticker,
    period="2y"
):

    try:

        data = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False
        )

        if data.empty:

            return pd.Series(
                dtype="float64"
            )


        # yfinance can return MultiIndex
        if isinstance(
            data.columns,
            pd.MultiIndex
        ):

            data = data["Close"]

            if hasattr(
                data,
                "columns"
            ):

                data = data.iloc[:, 0]

        else:

            data = data["Close"]


        return data.dropna()


    except Exception as error:

        print(
            f"Data error for {ticker}: {error}"
        )

        return pd.Series(
            dtype="float64"
        )


def latest_value(series):

    if series is None or len(series) == 0:

        return None

    return float(
        series.iloc[-1]
    )


def latest_date(series):

    if series is None or len(series) == 0:

        return None

    return series.index[-1].strftime(
        "%Y-%m-%d"
    )


def load_cape():

    path = ROOT / "data" / "cape.json"

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)
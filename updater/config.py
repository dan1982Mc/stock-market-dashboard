"""
Configuration for the Global Stock Market Dashboard.

Keep thresholds and ticker definitions here rather than scattering
them throughout update_market.py. This makes future patches easier.
"""

# ---------------------------------------------------------
# MARKET PROXIES
# ---------------------------------------------------------

TICKERS = {
    # Global
    "ACWI": "ACWI",

    # Developed Europe
    "Europe": "VGK",

    # Emerging markets
    "EM": "EEM",

    # United States
    "SP500": "^GSPC",

    # Volatility
    "VIX": "^VIX",
    "VSTOXX": "^V2TX",

    # Rates
    "US10Y": "^TNX",

    # Optional risk indicator
    "USD": "DX-Y.NYB"
}


# ---------------------------------------------------------
# TREND
# ---------------------------------------------------------

TREND_MA_SHORT = 50
TREND_MA_LONG = 200


# ---------------------------------------------------------
# DRAWDOWN
# ---------------------------------------------------------

DRAWDOWN_WARNING = -10
DRAWDOWN_STRESS = -20


# ---------------------------------------------------------
# VIX
# ---------------------------------------------------------

VIX_CALM = 15
VIX_NORMAL = 20
VIX_ELEVATED = 30
VIX_PANIC = 40


# ---------------------------------------------------------
# VSTOXX
# ---------------------------------------------------------

VSTOXX_CALM = 15
VSTOXX_NORMAL = 20
VSTOXX_ELEVATED = 30
VSTOXX_PANIC = 40


# ---------------------------------------------------------
# SCORE
# ---------------------------------------------------------

SCORE_BULLISH = 70
SCORE_NEUTRAL = 50
SCORE_CAUTION = 35


# ---------------------------------------------------------
# DATA SETTINGS
# ---------------------------------------------------------

HISTORY_PERIOD = "2y"

OUTPUT_FILE = "data/latest.json"

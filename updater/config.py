"""Configuration for V2 global market dashboard."""

TICKERS = {
    "ACWI": "ACWI",
    "US": "^GSPC",
    "Europe": "VGK",
    "EM": "EEM",
    "VIX": "^VIX",
    "US10Y": "^TNX",
    "GOLD": "GC=F",
}

HISTORY_PERIOD = "10y"
MA_SHORT = 50
MA_LONG = 200
OUTPUT_FILE = "data/latest.json"
HISTORY_FILE = "data/history.json"
CAPE_FILE = "data/cape.json"

# FRED public series (no API key required).
FRED_INFLATION = "T10YIE"
FRED_EM_VOL = "VXEEMCLS"

DRAWDOWN_WARNING = -10.0
DRAWDOWN_MAJOR = -20.0

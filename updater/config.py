"""Configuration for V2 global market dashboard."""

TICKERS = {
    "ACWI": "ACWI",
    "US": "^GSPC",
    "Europe": "VGK",
    "EM": "EEM",
    "VIX": "^VIX",
    "VSTOXX": "^V2TX",
    "EM_VIX": "^VXEEM",
    "US10Y": "^TNX",
    "GOLD": "GC=F",
}

HISTORY_PERIOD = "10y"
MA_SHORT = 50
MA_LONG = 200
OUTPUT_FILE = "data/latest.json"
HISTORY_FILE = "data/history.json"
CAPE_FILE = "data/cape.json"

# Optional FRED series. No API key is required for fredgraph.csv.
FRED_INFLATION = "T10YIE"

# Top-level market brief rules. These are intentionally simple and are
# not an investment recommendation engine yet.
DRAWDOWN_WARNING = -10.0
DRAWDOWN_MAJOR = -20.0

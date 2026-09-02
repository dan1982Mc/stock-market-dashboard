# Global Market Dashboard V2

A small, global market dashboard for a long-term ETF investor, with VWCE as the main reference portfolio.

## What V2 shows

- **Global equities:** ACWI, US, Europe and Emerging Markets trend relative to their 200-day moving average.
- **Risk:** US VIX, Europe VSTOXX, Emerging Markets VXEEM and ACWI drawdown.
- **Valuation:** US CAPE, shown against its historical percentile range.
- **Cross-asset:** US 10-year Treasury yield and gold.
- **What is priced in:** market-derived signals that are actually embedded in traded prices, currently option-implied equity volatility and inflation priced into bonds, plus equity valuation as context.
- **Weekly email:** a short Friday summary generated from the same `latest.json` data as the dashboard.

## How to read the bands

Every numerical indicator uses a 10-year historical distribution where enough history is available:

- P05 to P95 = the main historical range.
- P25 to P75 = the typical range inside it.
- The red line = today's value.
- The percentile tells where today's value sits in the historical distribution.

The top market brief is deliberately separate from the bands. It uses only three interpretations: **GOOD**, **WARNING**, and **MAJOR RISK**. It is a transparent summary, not a prediction score.

## Data flow

```text
Public market data
       ↓
updater/update_market_v2.py
       ↓
data/latest.json + data/history.json
       ↓
GitHub Pages dashboard
       ↓
weekly_email.yml → email_report.py
```

The frontend never calls Yahoo Finance or other external data sources directly.

## Automation

The market updater runs Monday-Friday at 06:30 UTC. The weekly brief runs Friday at 16:00 UTC.

Required repository secrets for email:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `EMAIL_TO`
- `DASHBOARD_URL`

## Local test

From the repository root:

```bash
pip install -r updater/requirements.txt
cd updater
python update_market_v2.py
cd ..
python -m http.server 8000
```

Open `http://localhost:8000`.

## Design principle

**Indicators describe the market. Personal investing rules determine the action.**

The V2 rebuild intentionally does not add sentiment surveys, dozens of macro indicators, or a composite 0-100 market score. Those can be considered later only if they improve the decisions this dashboard is meant to support.

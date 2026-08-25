# 🌍 Global Market Dashboard

A free/self-hosted global stock-market monitoring dashboard.

The dashboard is designed to answer:

1. What is the current global market regime?
2. Are markets expensive?
3. Is the trend healthy?
4. Is there market stress or panic?
5. Is the rally broad?
6. Are interest rates a headwind?
7. What action should a long-term investor consider?

---

# Architecture

The project intentionally separates:

DATA SOURCES
↓
INDICATOR CALCULATIONS
↓
SCORING
↓
JSON DATA
↓
DASHBOARD
↓
EMAIL

This makes future changes easier.

---

# Core indicators

## 1. Global Trend

Uses:

- ACWI
- 50-day moving average
- 200-day moving average
- momentum

---

## 2. Valuation

Uses:

- Global CAPE
- US CAPE
- Developed-market CAPE
- Emerging-market CAPE

CAPE is updated manually approximately quarterly.

File:

data/cape.json

---

## 3. Global Volatility

The dashboard does NOT treat VIX as global volatility.

It attempts to track:

- US VIX
- Europe VSTOXX
- Developed ex-US volatility
- Emerging-market volatility

Unavailable free feeds are displayed as unavailable rather than invented.

---

## 4. Global Breadth

The first version uses a regional benchmark proxy.

It measures the percentage of selected regional benchmarks above their 200-day moving average.

This is intentionally labelled as a proxy.

A future version can replace it with true constituent-level breadth.

---

## 5. Rates

Current implementation:

- US 10Y
- US 3M

Future versions can add:

- German 10Y
- real yields
- yield curve
- global financial conditions

---

## 6. Drawdown / Stress

Measures ACWI drawdown from its running high.

---

## 7. Sentiment

Low-weight confirmation signal.

It should never dominate the dashboard score.

---

# Score

Default weights:

Trend       20%
Valuation   20%
Volatility  15%
Breadth     15%
Rates       15%
Drawdown    10%
Sentiment    5%

The scoring model is located in:

updater/scoring.py

---

# CAPE

CAPE is intentionally not updated daily.

Update:

data/cape.json

approximately quarterly.

Never invent missing values.

---

# GitHub Actions

The normal update runs:

Monday-Friday
06:30 UTC

The weekly email runs:

Friday
16:00 UTC

GitHub Actions uses UTC.

---

# Email configuration

Create these GitHub repository secrets:

SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASSWORD
EMAIL_TO
DASHBOARD_URL

For Gmail, use an App Password rather than your normal Gmail password.

---

# Local testing

From the project root:

pip install -r requirements.txt

Then:

cd updater

python update_market.py

The generated file will be:

data/latest.json

Open index.html in a local web server.

For example:

python -m http.server 8000

Then open:

http://localhost:8000

---

# Future upgrades

The architecture is designed for incremental upgrades.

Possible future modules:

- true global breadth
- MSCI regional valuations
- forward P/E
- earnings revisions
- credit spreads
- global liquidity
- real yields
- dollar index
- gold
- oil
- Bitcoin
- put/call ratios
- market concentration
- S&P 500 CAPE percentile
- historical regime chart
- score history
- automatic alerts
- Telegram/Discord notifications

These should be added as independent modules rather than rewriting the dashboard.
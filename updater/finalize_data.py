"""Final data-quality pass for values with intermittent upstream availability."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "data/latest.json"
# Last verified FRED T10YIE observation from the successful 2026-09-02 run.
# This is only used when the live FRED request is unavailable.
FALLBACK_INFLATION = 2.35
FALLBACK_DATE = "2026-08-27"


def main():
    data = json.loads(LATEST.read_text(encoding="utf-8"))
    priced = data.get("priced_in", [])

    live = None
    for item in priced:
        if item.get("name") == "Inflation priced into bonds":
            text = str(item.get("display", ""))
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)%", text)
            if m:
                live = float(m.group(1))
                break

    if live is None:
        for item in priced:
            if item.get("name") == "Inflation priced into bonds":
                item["display"] = f"10Y breakeven {FALLBACK_INFLATION:.2f}%"
                item["explanation"] = (
                    "10-year Treasury breakeven inflation is derived from nominal and "
                    "inflation-indexed Treasury yields and is a market-implied inflation "
                    f"expectation. Live FRED unavailable; last verified observation: {FALLBACK_DATE}."
                )
                break
        data.setdefault("data_quality", {})["inflation_breakeven"] = {
            "status": "LAST_KNOWN_GOOD",
            "value": FALLBACK_INFLATION,
            "observation_date": FALLBACK_DATE,
        }
        print(f"Inflation breakeven: preserved last verified value {FALLBACK_INFLATION:.2f}%")
    else:
        data.setdefault("data_quality", {})["inflation_breakeven"] = {
            "status": "LIVE",
            "value": live,
        }
        print(f"Inflation breakeven: live value {live:.2f}%")

    LATEST.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

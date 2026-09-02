"""Weekly plain-text market brief generated from data/latest.json."""
import json
import os
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_data():
    return json.loads((ROOT / "data" / "latest.json").read_text(encoding="utf-8"))


def line_band(item):
    pct = item.get("percentile")
    return f"{item.get('display','—')} · P{int(pct)}" if pct is not None else item.get("display", "—")


def build_email(data):
    b = data.get("brief", {})
    lines = [
        "GLOBAL MARKET — WEEKLY BRIEF",
        f"Week ending: {data.get('data_through','—')}",
        "",
        f"{b.get('status','—')} — {b.get('label','—')}",
        b.get("reason", ""),
        "",
        "GLOBAL EQUITIES",
    ]
    for item in data.get("equities", []):
        lines.append(f"{item['name']}: {line_band(item)}")
    lines += ["", "MARKET RISK"]
    for item in data.get("risk", []):
        lines.append(f"{item['name']}: {line_band(item)}")
    lines += ["", "VALUATION & CROSS-ASSET"]
    for item in data.get("valuation", []) + data.get("cross_asset", []):
        lines.append(f"{item['name']}: {line_band(item)}")
    lines += ["", "WHAT IS PRICED IN"]
    for item in data.get("priced_in", []):
        lines.append(f"{item['name']}: {item['display']} — {item['explanation']}")
    lines += ["", "CURRENT PLAN", data.get("rules", {}).get("action", "NORMAL DCA"), "", "Dashboard:", os.environ.get("DASHBOARD_URL", "Dashboard URL not configured"), "", "Informational only; not investment advice."]
    return "\n".join(lines)


def send_email():
    data = load_data()
    body = build_email(data)
    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = f"Global Market Weekly — {data.get('brief',{}).get('label','Market update')}"
    message["From"] = os.environ["SMTP_USER"]
    message["To"] = os.environ["EMAIL_TO"]
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587"))) as server:
        server.starttls()
        server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        server.send_message(message)


if __name__ == "__main__":
    send_email()

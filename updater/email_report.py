"""
WEEKLY EMAIL

The email is generated from data/latest.json.

It does not calculate another market score.
"""

import json
import os
import smtplib

from email.mime.text import MIMEText
from pathlib import Path


ROOT =
    Path(__file__).resolve().parents[1]


def load_data():

    with open(
        ROOT /
        "data" /
        "latest.json",
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def build_email(data):

    overall =
        data["overall"]


    lines = [

        "GLOBAL MARKET WEEKLY",

        f"Week ending: "
        f"{data['data_through']}",

        "",

        f"{overall['emoji']} "
        f"{overall['label']} "
        f"— {overall['score']}/100",

        "",

        "RECOMMENDED ACTION",

        overall["action"],

        "",

        overall["reason"],

        "",

        "CORE INDICATORS",

        ""
    ]


    for indicator in data["indicators"]:

        lines.append(

            f"{indicator['emoji']} "
            f"{indicator['name']}: "
            f"{indicator['status']} — "
            f"{indicator['value']}"
        )


    lines += [

        "",

        "WHAT MATTERS NOW",

        ""
    ]


    for item in data["what_matters"]:

        lines.append(
            f"• {item}"
        )


    lines += [

        "",

        "WATCH NEXT WEEK",

        ""
    ]


    for item in data["watch"]:

        lines.append(
            f"• {item}"
        )


    lines += [

        "",

        "Dashboard:",

        os.environ.get(
            "DASHBOARD_URL",
            "Dashboard URL not configured"
        ),

        "",

        "This dashboard is "
        "informational only and "
        "is not investment advice."
    ]


    return "\n".join(lines)


def send_email():

    data =
        load_data()


    body =
        build_email(
            data
        )


    message =
        MIMEText(
            body,
            "plain",
            "utf-8"
        )


    message["Subject"] = (

        "Global Market Weekly — "
        f"{data['overall']['emoji']} "
        f"{data['overall']['label']}"
    )


    message["From"] =
        os.environ["SMTP_USER"]


    message["To"] =
        os.environ["EMAIL_TO"]


    with smtplib.SMTP(
        os.environ["SMTP_HOST"],
        int(
            os.environ.get(
                "SMTP_PORT",
                "587"
            )
        )
    ) as server:

        server.starttls()

        server.login(

            os.environ["SMTP_USER"],

            os.environ["SMTP_PASSWORD"]
        )

        server.send_message(
            message
        )


if __name__ == "__main__":

    send_email()
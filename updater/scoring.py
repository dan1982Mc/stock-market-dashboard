"""
SCORING ENGINE

This converts indicator states into the
0-100 Global Market Score.

Change the scoring philosophy here without
touching data collection or the dashboard.
"""


STATUS_SCORES = {

    "BULLISH": 85,
    "HEALTHY": 80,
    "ATTRACTIVE": 85,
    "NORMAL": 75,

    "NEUTRAL": 55,
    "MIXED": 50,
    "ELEVATED": 40,

    "EXPENSIVE": 30,
    "RESTRICTIVE": 35,
    "CAUTION": 35,

    "CORRECTION": 55,
    "MAJOR_CORRECTION": 30,

    "STRESS": 15,
    "BEARISH": 15,
    "WEAK": 25,

    "EXTREME": 10,
    "PANIC": 5,

    "UNAVAILABLE": 50
}


def status_score(
    status
):

    return STATUS_SCORES.get(
        status,
        50
    )


def calculate_score(
    states,
    weights
):

    total_weight = 0
    weighted_score = 0

    breakdown = {}


    for name, weight in weights.items():

        status =
            states.get(
                name,
                "UNAVAILABLE"
            )


        score =
            status_score(
                status
            )


        weighted_score += (
            score * weight
        )

        total_weight += weight


        breakdown[name] = {

            "status": status,

            "score": score,

            "weight": weight,

            "contribution":
                round(
                    score *
                    weight /
                    100,
                    1
                )
        }


    if total_weight == 0:

        return 50, breakdown


    final_score = round(
        weighted_score /
        total_weight
    )


    return final_score, breakdown


def market_regime(
    score
):

    if score >= 75:

        return {
            "label": "BULLISH",
            "emoji": "🟢",
            "class": "green",
            "action": "CONTINUE NORMAL DCA"
        }


    if score >= 55:

        return {
            "label": "NEUTRAL",
            "emoji": "🟡",
            "class": "yellow",
            "action": "CONTINUE NORMAL DCA"
        }


    if score >= 40:

        return {
            "label": "CAUTION",
            "emoji": "🟠",
            "class": "orange",
            "action":
                "HOLD / AVOID AGGRESSIVE LUMP SUM"
        }


    return {

        "label":
            "STRESS / POTENTIAL OPPORTUNITY",

        "emoji": "🔴",

        "class": "red",

        "action":
            "DO NOT PANIC SELL; CONSIDER STAGED BUYING"
    }
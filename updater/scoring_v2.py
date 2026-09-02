"""Transparent V2 market brief. No composite 0-100 score."""


def market_brief(acwi_trend, drawdown, vix, vstoxx, em_vix):
    vols = [x for x in (vix, vstoxx, em_vix) if x is not None]
    major = (acwi_trend is not None and acwi_trend < 0 and drawdown is not None and drawdown <= -20)
    warning = (acwi_trend is not None and acwi_trend < 0) or (drawdown is not None and drawdown <= -10)
    if sum(x >= 30 for x in vols) >= 2:
        major = True
    elif any(x >= 25 for x in vols):
        warning = True
    if major:
        return {"status":"MAJOR RISK","label":"MAJOR RISK","reason":"Global trend, drawdown and/or volatility indicate a materially stressed equity environment."}
    if warning:
        return {"status":"WARNING","label":"WARNING / MIXED","reason":"At least one important global market condition is deteriorating. The dashboard is monitoring the situation rather than predicting a turn."}
    return {"status":"GOOD","label":"GOOD / HEALTHY","reason":"Global trend is positive, drawdown is contained and market volatility is not unusually high."}


def rules_placeholder():
    return {"action":"NORMAL DCA","detail":"The personal investing rules are intentionally separate from market scoring and will be added later."}

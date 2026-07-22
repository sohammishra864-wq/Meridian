from datetime import date
from typing import Optional


def calc_cash_runway(
    cash: float,
    monthly_burn_rate: float,
    period_start: date,
    period_end: date,
) -> Optional[dict]:
    """Cash Runway = Cash / Monthly Burn Rate"""
    if monthly_burn_rate <= 0:
        return None  # ponytail: profitable companies have infinite runway, skip

    runway_months = cash / monthly_burn_rate
    return {
        "metric_type": "CASH_RUNWAY_MONTHS",
        "value": round(runway_months, 1),
        "unit": "months",
        "valid_from": period_start,
        "valid_to": period_end,
        "computation_method": "calc_cash_runway",
        "xbrl_concepts_used": ["CashAndCashEquivalents", "NetCashProvidedByUsedInOperatingActivities"],
    }

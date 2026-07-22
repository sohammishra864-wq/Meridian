from datetime import date
from typing import Optional


def calc_roic_nopat(
    nopat: float,
    invested_capital: float,
    period_start: date,
    period_end: date,
) -> Optional[dict]:
    """
    ROIC = NOPAT / Invested Capital
    Returns metric dict or None if calculation invalid.
    """
    if invested_capital <= 0:
        return None  # ponytail: avoid division by zero, skip invalid data

    roic = nopat / invested_capital
    return {
        "metric_type": "ROIC",
        "value": round(roic, 4),
        "unit": "ratio",
        "valid_from": period_start,
        "valid_to": period_end,
        "computation_method": "calc_roic_nopat",
        "xbrl_concepts_used": ["NOPAT", "InvestedCapital"],
    }

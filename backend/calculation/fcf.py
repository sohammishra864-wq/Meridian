from datetime import date
from typing import Optional


def calc_fcf(
    operating_cash_flow: float,
    capex: float,
    period_start: date,
    period_end: date,
) -> dict:
    """FCF = Operating Cash Flow - CapEx"""
    fcf = operating_cash_flow - abs(capex)
    return {
        "metric_type": "FCF",
        "value": round(fcf, 2),
        "unit": "USD",
        "valid_from": period_start,
        "valid_to": period_end,
        "computation_method": "calc_fcf",
        "xbrl_concepts_used": ["NetCashProvidedByUsedInOperatingActivities", "PaymentsToAcquirePropertyPlantAndEquipment"],
    }

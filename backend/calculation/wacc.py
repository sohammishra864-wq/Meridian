from datetime import date
from typing import Optional


def calc_wacc(
    risk_free_rate: float,
    beta: float,
    market_risk_premium: float,
    debt: float,
    equity_market_cap: float,
    tax_rate: float,
    period_start: date,
    period_end: date,
) -> Optional[dict]:
    """
    WACC = (E / (E + D)) * Re + (D / (E + D)) * Rd * (1 - Tax)
    Re = Rf + Beta * MRP (CAPM)
    """
    total_capital = equity_market_cap + debt
    if total_capital <= 0:
        return None

    cost_of_equity = risk_free_rate + beta * market_risk_premium
    cost_of_debt = 0.05  # ponytail: stub, derive from debt_instruments in Phase 2
    wacc = (equity_market_cap / total_capital) * cost_of_equity + (debt / total_capital) * cost_of_debt * (1 - tax_rate)

    return {
        "metric_type": "WACC",
        "value": round(wacc, 4),
        "unit": "ratio",
        "valid_from": period_start,
        "valid_to": period_end,
        "computation_method": "calc_wacc",
        "methodology_note": f"CAPM: Rf={risk_free_rate}, Beta={beta}, MRP={market_risk_premium}",
        "xbrl_concepts_used": ["LongTermDebt", "MarketCap"],
    }

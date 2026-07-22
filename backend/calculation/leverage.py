from datetime import date


def calc_gross_margin(
    revenue: float,
    cogs: float,
    period_start: date,
    period_end: date,
) -> dict:
    """Gross Margin = (Revenue - COGS) / Revenue"""
    margin = (revenue - cogs) / revenue if revenue > 0 else 0
    return {
        "metric_type": "GROSS_MARGIN",
        "value": round(margin, 4),
        "unit": "ratio",
        "valid_from": period_start,
        "valid_to": period_end,
        "computation_method": "calc_gross_margin",
        "xbrl_concepts_used": ["Revenue", "CostOfRevenue"],
    }


def calc_operating_margin(
    operating_income: float,
    revenue: float,
    period_start: date,
    period_end: date,
) -> dict:
    """Operating Margin = Operating Income / Revenue"""
    margin = operating_income / revenue if revenue > 0 else 0
    return {
        "metric_type": "OPERATING_MARGIN",
        "value": round(margin, 4),
        "unit": "ratio",
        "valid_from": period_start,
        "valid_to": period_end,
        "computation_method": "calc_operating_margin",
        "xbrl_concepts_used": ["OperatingIncome", "Revenue"],
    }


def calc_net_debt(
    total_debt: float,
    cash: float,
    period_start: date,
    period_end: date,
) -> dict:
    """Net Debt = Total Debt - Cash"""
    net_debt = total_debt - cash
    return {
        "metric_type": "NET_DEBT",
        "value": round(net_debt, 2),
        "unit": "USD",
        "valid_from": period_start,
        "valid_to": period_end,
        "computation_method": "calc_net_debt",
        "xbrl_concepts_used": ["LongTermDebt", "ShortTermDebt", "CashAndCashEquivalents"],
    }

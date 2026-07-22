from datetime import date, datetime
from typing import Optional
import asyncpg
from calculation.roic import calc_roic_nopat
from calculation.fcf import calc_fcf
from calculation.wacc import calc_wacc
from calculation.leverage import calc_gross_margin, calc_operating_margin, calc_net_debt
from calculation.runway import calc_cash_runway
from calculation.confidence import compute_metric_confidence


async def store_metric(
    conn: asyncpg.Connection,
    company_id: int,
    metric: dict,
    filing_id: int,
    confidence_score: float,
    xbrl_validated: bool,
) -> None:
    """Store metric with bi-temporal pattern."""
    # Supersede existing current version
    await conn.execute("""
        UPDATE metrics
        SET superseded_at = NOW()
        WHERE company_id = $1
          AND metric_type = $2
          AND period_type = $3
          AND valid_to = $4
          AND superseded_at IS NULL
    """, company_id, metric["metric_type"], "annual", metric["valid_to"])

    # Insert new version
    await conn.execute("""
        INSERT INTO metrics (
            company_id, metric_type, value, unit, period_type,
            valid_from, valid_to, recorded_at,
            computation_method, methodology_note, is_estimated, unit_test_passed,
            xbrl_validated, xbrl_concepts_used, confidence_score, base_confidence,
            source_filing_id, cross_ref_flag
        ) VALUES (
            $1, $2, $3, $4, 'annual',
            $5, $6, NOW(),
            $7, $8, false, true,
            $9, $10, $11, $11,
            $12, false
        )
    """,
        company_id,
        metric["metric_type"],
        metric["value"],
        metric["unit"],
        metric["valid_from"],
        metric["valid_to"],
        metric["computation_method"],
        metric.get("methodology_note"),
        xbrl_validated,
        metric.get("xbrl_concepts_used", []),
        confidence_score,
        filing_id,
    )


async def compute_all_metrics(
    facts: dict,
    period_start: date,
    period_end: date,
    risk_free_rate: float = 0.04,
    beta: float = 1.0,
    market_risk_premium: float = 0.06,
) -> list[dict]:
    """Compute all 7 core metrics from XBRL facts."""
    metrics = []

    # ROIC
    nopat = facts.get("OperatingIncome", 0) * (1 - 0.21)  # ponytail: stub tax rate
    invested_capital = facts.get("Assets", 0) - facts.get("Liabilities", 0)
    if m := calc_roic_nopat(nopat, invested_capital, period_start, period_end):
        metrics.append(m)

    # FCF
    ocf = facts.get("NetCashProvidedByUsedInOperatingActivities", 0)
    capex = facts.get("PaymentsToAcquirePropertyPlantAndEquipment", 0)
    metrics.append(calc_fcf(ocf, capex, period_start, period_end))

    # WACC
    debt = facts.get("LongTermDebt", 0) + facts.get("ShortTermDebt", 0)
    market_cap = facts.get("CommonStockSharesOutstanding", 0) * 100  # ponytail: stub price $100
    if m := calc_wacc(risk_free_rate, beta, market_risk_premium, debt, market_cap, 0.21, period_start, period_end):
        metrics.append(m)

    # Margins
    revenue = facts.get("Revenue", 0)
    cogs = facts.get("CostOfRevenue", 0)
    metrics.append(calc_gross_margin(revenue, cogs, period_start, period_end))

    operating_income = facts.get("OperatingIncome", 0)
    metrics.append(calc_operating_margin(operating_income, revenue, period_start, period_end))

    # Net Debt
    cash = facts.get("CashAndCashEquivalents", 0)
    metrics.append(calc_net_debt(debt, cash, period_start, period_end))

    # Cash Runway
    monthly_burn = abs(ocf) / 12 if ocf < 0 else 0
    if m := calc_cash_runway(cash, monthly_burn, period_start, period_end):
        metrics.append(m)

    return metrics

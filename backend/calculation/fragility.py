"""Fragility scoring engine - Epic 5a."""

from datetime import date
import asyncpg
import json


async def compute_fragility_score(
    company_id: int,
    db: asyncpg.Connection
) -> dict:
    """
    Compute fragility score for a company.

    Scoring rules:
    - ROIC < WACC: +20 points
    - Debt maturity in next 12 months > cash reserves: +30 points
    - Cash runway < 12 months: +25 points
    - Sanctioned entity (OFAC/BIS): +25 points
    """
    # ponytail: one query for all metrics instead of four
    metrics = await db.fetch("""
        SELECT metric_type, value FROM metrics
        WHERE company_id = $1 AND metric_type IN ('ROIC','WACC','CASH_RUNWAY','NET_DEBT')
          AND superseded_at IS NULL
        ORDER BY valid_to DESC
    """, company_id)
    m = {r['metric_type']: float(r['value']) for r in metrics}

    # Get company info + sanctions in one query
    company = await db.fetchrow("""
        SELECT e.canonical_name, c.ticker, e.is_sanctioned, e.is_on_bis_list
        FROM companies c
        JOIN entity_master e ON c.entity_master_id = e.id
        WHERE c.id = $1
    """, company_id)

    if not company:
        return {'score': 0, 'breakdown': {}, 'company_name': None, 'ticker': None}

    # Debt maturity check
    next_year = date.today().year + 1
    debt_maturing = await db.fetchval("""
        SELECT COALESCE(SUM(amount), 0)
        FROM debt_instruments
        WHERE company_id = $1 AND maturity_year <= $2
    """, company_id, next_year)

    # ponytail: build breakdown in one pass instead of mutating empty dict
    roic_val, wacc_val = m.get('ROIC'), m.get('WACC')
    runway_val = m.get('CASH_RUNWAY')
    cash_reserves = max(0, -m.get('NET_DEBT', 0))  # net debt < 0 means cash
    is_sanctioned = company['is_sanctioned'] or company['is_on_bis_list']

    roic_risk = 20 if (roic_val and wacc_val and roic_val < wacc_val) else 0
    debt_risk = 30 if debt_maturing > cash_reserves else 0
    runway_risk = 25 if (runway_val and runway_val < 12) else 0
    sanction_risk = 25 if is_sanctioned else 0

    score = min(roic_risk + debt_risk + runway_risk + sanction_risk, 100)

    return {
        'score': score,
        'breakdown': {
            'roic_below_wacc': roic_risk,
            'debt_maturity_risk': debt_risk,
            'cash_runway_risk': runway_risk,
            'sanctions_risk': sanction_risk,
            'details': {
                'roic': roic_val,
                'wacc': wacc_val,
                'debt_maturing_12m': float(debt_maturing),
                'cash_reserves': cash_reserves,
                'cash_runway_months': runway_val,
                'is_sanctioned': is_sanctioned
            }
        },
        'company_name': company['canonical_name'],
        'ticker': company['ticker']
    }


async def store_fragility_score(
    company_id: int,
    score: int,
    breakdown: dict,
    db: asyncpg.Connection
) -> int:
    """Store fragility score in database."""
    # ponytail: store only score + breakdown JSON, no redundant _points columns
    result = await db.fetchrow("""
        INSERT INTO fragility_scores (company_id, score, breakdown)
        VALUES ($1, $2, $3)
        RETURNING id
    """, company_id, score, json.dumps(breakdown))

    return result['id']

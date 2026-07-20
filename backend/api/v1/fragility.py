"""Fragility screening API - Epic 5a."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from core.database import get_db
import asyncpg
import json
from calculation.fragility import compute_fragility_score, store_fragility_score


router = APIRouter(tags=["fragility"])


class FragilityBreakdown(BaseModel):
    roic_below_wacc: int
    debt_maturity_risk: int
    cash_runway_risk: int
    sanctions_risk: int
    details: dict


class FragilityScore(BaseModel):
    company_id: int
    company_name: str
    ticker: str | None
    score: int
    computed_at: str
    breakdown: FragilityBreakdown


class FragilityScreenItem(BaseModel):
    company_id: int
    company_name: str
    ticker: str | None
    score: int
    roic: float | None
    wacc: float | None
    debt_maturity_12m: float | None
    cash_runway_months: float | None
    is_sanctioned: bool


@router.get("/fragility/screen", response_model=List[FragilityScreenItem])
async def fragility_screen(db: asyncpg.Connection = Depends(get_db)):
    """Fragility screen - all companies ranked by score."""
    rows = await db.fetch("""
        SELECT
            c.id as company_id,
            e.canonical_name as company_name,
            c.ticker,
            fs.score,
            fs.breakdown,
            e.is_sanctioned OR e.is_on_bis_list as is_sanctioned
        FROM fragility_scores fs
        JOIN companies c ON fs.company_id = c.id
        JOIN entity_master e ON c.entity_master_id = e.id
        ORDER BY fs.score DESC
    """)

    # ponytail: list comp instead of append loop
    return [
        {
            'company_id': r['company_id'],
            'company_name': r['company_name'],
            'ticker': r['ticker'],
            'score': r['score'],
            'roic': details.get('roic'),
            'wacc': details.get('wacc'),
            'debt_maturity_12m': details.get('debt_maturing_12m'),
            'cash_runway_months': details.get('cash_runway_months'),
            'is_sanctioned': r['is_sanctioned']
        }
        for r in rows
        for bd in [json.loads(r['breakdown']) if isinstance(r['breakdown'], str) else (r['breakdown'] or {})]
        for details in [bd.get('details', {})]
    ]


@router.get("/companies/{company_id}/fragility", response_model=FragilityScore)
async def get_company_fragility(
    company_id: int,
    recompute: bool = False,
    db: asyncpg.Connection = Depends(get_db)
):
    """Get fragility score. If recompute=true, recalculates from latest metrics."""
    if recompute:
        # ponytail: compute_fragility_score now returns company_name/ticker
        result = await compute_fragility_score(company_id, db)
        if not result['company_name']:
            raise HTTPException(404, "Company not found")

        await store_fragility_score(company_id, result['score'], result['breakdown'], db)

        return {
            'company_id': company_id,
            'company_name': result['company_name'],
            'ticker': result['ticker'],
            'score': result['score'],
            'computed_at': 'just now',
            'breakdown': result['breakdown']
        }

    # Fetch latest stored score
    row = await db.fetchrow("""
        SELECT fs.score, fs.computed_at, fs.breakdown, e.canonical_name, c.ticker
        FROM fragility_scores fs
        JOIN companies c ON fs.company_id = c.id
        JOIN entity_master e ON c.entity_master_id = e.id
        WHERE fs.company_id = $1
        ORDER BY fs.computed_at DESC LIMIT 1
    """, company_id)

    if not row:
        raise HTTPException(404, "No fragility score found. Use recompute=true to generate.")

    return {
        'company_id': company_id,
        'company_name': row['canonical_name'],
        'ticker': row['ticker'],
        'score': row['score'],
        'computed_at': row['computed_at'].isoformat(),
        'breakdown': row['breakdown']
    }

"""Risk management API - Epic 5b."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from core.database import get_db
import asyncpg
from intelligence.risk_generation import generate_risks_for_company, store_risk


router = APIRouter(tags=["risks"])


class Risk(BaseModel):
    id: int | None
    company_id: int
    risk_type: str
    severity: str
    description: str
    source_basis: str
    valid_from: str
    valid_to: str | None
    created_at: str | None


@router.get("/companies/{company_id}/risks", response_model=List[Risk])
async def get_company_risks(
    company_id: int,
    active_only: bool = True,
    db: asyncpg.Connection = Depends(get_db)
):
    """Get risks for a company."""
    query = """
        SELECT id, company_id, risk_type, severity, description,
               source_basis, valid_from, valid_to, created_at
        FROM risks
        WHERE company_id = $1
    """

    if active_only:
        query += " AND (valid_to IS NULL OR valid_to >= CURRENT_DATE)"

    query += " ORDER BY severity DESC, created_at DESC"

    rows = await db.fetch(query, company_id)

    return [
        {
            'id': r['id'],
            'company_id': r['company_id'],
            'risk_type': r['risk_type'],
            'severity': r['severity'],
            'description': r['description'],
            'source_basis': r['source_basis'],
            'valid_from': r['valid_from'].isoformat(),
            'valid_to': r['valid_to'].isoformat() if r['valid_to'] else None,
            'created_at': r['created_at'].isoformat() if r['created_at'] else None
        }
        for r in rows
    ]


@router.post("/companies/{company_id}/risks/generate")
async def generate_risks(
    company_id: int,
    db: asyncpg.Connection = Depends(get_db)
):
    """Auto-generate risks for a company based on deterministic rules."""
    risks = await generate_risks_for_company(company_id, db)

    if not risks:
        return {'company_id': company_id, 'risks_generated': 0, 'message': 'No risks detected'}

    # Store risks
    risk_ids = []
    for risk in risks:
        risk_id = await store_risk(company_id, risk, db)
        risk_ids.append(risk_id)

    return {
        'company_id': company_id,
        'risks_generated': len(risk_ids),
        'risk_ids': risk_ids
    }

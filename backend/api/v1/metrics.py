from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from core.database import get_db
import asyncpg

router = APIRouter(tags=["metrics"])


@router.get("/companies/{company_id}/metrics")
async def get_company_metrics(
    company_id: int,
    metric_type: Optional[str] = None,
    db: asyncpg.Connection = Depends(get_db)
):
    """Get current metrics for a company."""
    if metric_type:
        query = """
            SELECT metric_type, value, unit, period_type, valid_from, valid_to,
                   confidence_score, computation_method, xbrl_concepts_used, recorded_at
            FROM metrics
            WHERE company_id = $1 AND metric_type = $2 AND superseded_at IS NULL
            ORDER BY valid_to DESC
        """
        rows = await db.fetch(query, company_id, metric_type)
    else:
        query = """
            SELECT metric_type, value, unit, period_type, valid_from, valid_to,
                   confidence_score, computation_method, xbrl_concepts_used, recorded_at
            FROM metrics
            WHERE company_id = $1 AND superseded_at IS NULL
            ORDER BY metric_type, valid_to DESC
        """
        rows = await db.fetch(query, company_id)

    if not rows:
        raise HTTPException(status_code=404, detail="No metrics found")

    return {
        "company_id": company_id,
        "metrics": [dict(row) for row in rows]
    }


@router.get("/companies/{company_id}/metrics/history")
async def get_metric_history(
    company_id: int,
    metric_type: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """Get bi-temporal history for a specific metric."""
    query = """
        SELECT value, valid_from, valid_to, recorded_at, superseded_at,
               confidence_score, computation_method
        FROM metrics
        WHERE company_id = $1 AND metric_type = $2
        ORDER BY valid_to DESC, recorded_at DESC
    """
    rows = await db.fetch(query, company_id, metric_type)

    if not rows:
        raise HTTPException(status_code=404, detail="No history found")

    return {
        "company_id": company_id,
        "metric_type": metric_type,
        "history": [dict(row) for row in rows]
    }

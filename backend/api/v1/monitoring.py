"""Monitoring API endpoints for data quality dashboard."""

from fastapi import APIRouter, Depends
from core.database import get_db
import asyncpg
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/queue-status")
async def get_queue_status(conn: asyncpg.Connection = Depends(get_db)) -> Dict[str, Any]:
    """Get sync_queue status for dashboard."""
    pending = await conn.fetchval(
        "SELECT COUNT(*) FROM sync_queue WHERE status = 'pending'"
    )
    failed = await conn.fetchval(
        "SELECT COUNT(*) FROM sync_queue WHERE status = 'failed'"
    )
    completed = await conn.fetchval(
        "SELECT COUNT(*) FROM sync_queue WHERE status = 'completed'"
    )

    return {
        "pending": pending,
        "failed": failed,
        "completed": completed,
    }


@router.get("/jobs")
async def get_jobs(
    status: Optional[str] = None,
    limit: int = 100,
    conn: asyncpg.Connection = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get data_refresh_jobs for dashboard."""
    if status:
        rows = await conn.fetch(
            """
            SELECT id, job_type, entity_id, status, attempts, max_attempts,
                   error_msg, created_at, started_at, completed_at
            FROM data_refresh_jobs
            WHERE status = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            status, limit
        )
    else:
        rows = await conn.fetch(
            """
            SELECT id, job_type, entity_id, status, attempts, max_attempts,
                   error_msg, created_at, started_at, completed_at
            FROM data_refresh_jobs
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit
        )

    return [dict(row) for row in rows]


@router.get("/alerts")
async def get_alerts(
    severity: Optional[str] = None,
    resolved: bool = False,
    limit: int = 100,
    conn: asyncpg.Connection = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get monitoring alerts for dashboard."""
    query = """
        SELECT ma.id, ma.alert_type, ma.severity, ma.description,
               ma.company_id, ma.metric_id, ma.created_at, ma.resolved_at,
               em.canonical_name as company_name
        FROM monitoring_alerts ma
        LEFT JOIN companies c ON ma.company_id = c.id
        LEFT JOIN entity_master em ON c.entity_master_id = em.id
        WHERE 1=1
    """
    params = []

    if severity:
        params.append(severity)
        query += f" AND ma.severity = ${len(params)}"

    if not resolved:
        query += " AND ma.resolved_at IS NULL"

    params.append(limit)
    query += f" ORDER BY ma.created_at DESC LIMIT ${len(params)}"

    rows = await conn.fetch(query, *params)
    return [dict(row) for row in rows]


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    conn: asyncpg.Connection = Depends(get_db)
) -> Dict[str, str]:
    """Mark an alert as resolved."""
    await conn.execute(
        "UPDATE monitoring_alerts SET resolved_at = CURRENT_TIMESTAMP WHERE id = $1",
        alert_id
    )
    return {"status": "resolved"}


@router.get("/confidence-distribution")
async def get_confidence_distribution(
    conn: asyncpg.Connection = Depends(get_db)
) -> Dict[str, int]:
    """
    Get histogram of metric confidence scores.

    Returns count per confidence band: 0-0.5, 0.5-0.7, 0.7-0.85, 0.85-1.0
    """
    rows = await conn.fetch("""
        SELECT
            CASE
                WHEN confidence_score < 0.5 THEN '0.0-0.5'
                WHEN confidence_score < 0.7 THEN '0.5-0.7'
                WHEN confidence_score < 0.85 THEN '0.7-0.85'
                ELSE '0.85-1.0'
            END as band,
            COUNT(*) as count
        FROM metrics
        WHERE superseded_at IS NULL
        GROUP BY band
        ORDER BY band
    """)

    return {row['band']: row['count'] for row in rows}


@router.post("/test-confidence-check")
async def test_confidence_check(conn: asyncpg.Connection = Depends(get_db)) -> Dict[str, str]:
    """Manual trigger for confidence monitoring (testing only)."""
    from monitoring.alerts import check_confidence_alerts
    await check_confidence_alerts(conn)
    return {"status": "checked"}

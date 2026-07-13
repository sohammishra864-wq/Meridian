"""Company search API - v1."""

from fastapi import APIRouter, Depends
import asyncpg
from typing import List
from pydantic import BaseModel


router = APIRouter(prefix="/companies", tags=["companies"])


class CompanySearchResult(BaseModel):
    id: int
    canonical_name: str
    ticker: str | None
    lei: str | None
    is_sanctioned: bool
    is_on_bis_list: bool


@router.get("/search", response_model=List[CompanySearchResult])
async def search_companies(q: str):
    """Search companies by name (PostgreSQL FTS)."""
    from main import pg_pool

    async with pg_pool.acquire() as conn:
        # ponytail: full-text search via ILIKE for MVP, pg_trgm for production
        rows = await conn.fetch("""
            SELECT
                c.id,
                e.canonical_name,
                c.ticker,
                e.lei,
                e.is_sanctioned,
                e.is_on_bis_list
            FROM companies c
            JOIN entity_master e ON c.entity_master_id = e.id
            WHERE e.canonical_name ILIKE $1
            LIMIT 20
        """, f'%{q}%')

        return [dict(row) for row in rows]

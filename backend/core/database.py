from typing import AsyncGenerator
import asyncpg

# Global pool - initialized by main.py lifespan
_pg_pool: asyncpg.Pool = None


def set_pg_pool(pool: asyncpg.Pool):
    """Set global connection pool."""
    global _pg_pool
    _pg_pool = pool


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """FastAPI dependency for database connection."""
    async with _pg_pool.acquire() as conn:
        yield conn

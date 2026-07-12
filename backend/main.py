from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncpg
from neo4j import AsyncGraphDatabase
from core.neo4j_init import initialize_neo4j_schema
from core.sync_worker import process_sync_queue
from core.database import set_pg_pool
from core.logging_config import configure_logging
from api.v1.graph import set_neo4j_driver
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os

# Configure structured JSON logging
configure_logging()

# Database connections (global, initialized on startup)
pg_pool = None
neo4j_driver = None
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global pg_pool, neo4j_driver, scheduler

    # Startup
    # PostgreSQL connection pool
    pg_pool = await asyncpg.create_pool(
        os.getenv("DATABASE_URL"),
        min_size=2,
        max_size=10,
    )

    # Neo4j driver
    neo4j_driver = AsyncGraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")),
    )

    # Verify connections
    async with pg_pool.acquire() as conn:
        await conn.fetchval("SELECT 1")

    async with neo4j_driver.session() as session:
        result = await session.run("RETURN 1 AS test")
        await result.single()

    # Set global pool for FastAPI dependencies
    set_pg_pool(pg_pool)
    set_neo4j_driver(neo4j_driver)

    # Initialize Neo4j schema
    await initialize_neo4j_schema(neo4j_driver)

    # Start APScheduler for sync worker + monitoring
    scheduler = AsyncIOScheduler()

    # Lightweight job: sync worker (every 30s)
    scheduler.add_job(
        process_sync_queue,
        'interval',
        seconds=30,
        args=[pg_pool, neo4j_driver],
        id='sync_worker',
    )

    # Lightweight job: confidence monitoring (daily at 2am UTC)
    from monitoring.alerts import check_confidence_alerts
    async def run_confidence_check():
        async with pg_pool.acquire() as conn:
            await check_confidence_alerts(conn)

    scheduler.add_job(
        run_confidence_check,
        'cron',
        hour=2,
        minute=0,
        id='confidence_monitor',
    )

    scheduler.start()

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    await pg_pool.close()
    await neo4j_driver.close()


app = FastAPI(title="Meridian API", version="0.1.0", lifespan=lifespan)

# Include v1 API router
from api.v1 import router as v1_router
app.include_router(v1_router)


@app.get("/health")
async def health_check():
    """Health check endpoint - verifies both databases are accessible."""
    postgres_ok = False
    neo4j_ok = False

    try:
        async with pg_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        postgres_ok = True
    except Exception as e:
        print(f"Postgres health check failed: {e}")

    try:
        async with neo4j_driver.session() as session:
            result = await session.run("RETURN 1 AS test")
            await result.single()
        neo4j_ok = True
    except Exception as e:
        print(f"Neo4j health check failed: {e}")

    status = "ok" if (postgres_ok and neo4j_ok) else "degraded"

    return {
        "status": status,
        "postgres": "ok" if postgres_ok else "error",
        "neo4j": "ok" if neo4j_ok else "error",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Meridian API v0.1.0"}

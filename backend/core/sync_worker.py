"""Sync worker - processes sync_queue to update Neo4j."""

from neo4j import AsyncDriver
import asyncpg
import json


from .sync_handlers import sync_company_to_neo4j, sync_person_to_neo4j, sync_country_to_neo4j

SYNC_HANDLERS = {
    'company': sync_company_to_neo4j,
    'person': sync_person_to_neo4j,
    'country': sync_country_to_neo4j,
}


async def process_sync_queue(pg_pool: asyncpg.Pool, neo4j_driver: AsyncDriver) -> None:
    """
    Process pending sync_queue entries.

    Called by APScheduler every 30s. Idempotent via MERGE in Neo4j.
    """
    async with pg_pool.acquire() as conn:
        # Get pending jobs (with row lock to prevent double-processing)
        rows = await conn.fetch("""
            SELECT id, entity_type, entity_id, operation, payload, attempts
            FROM sync_queue
            WHERE status = 'pending' AND attempts < 3
            ORDER BY created_at
            LIMIT 50
            FOR UPDATE SKIP LOCKED
        """)

        for row in rows:
            handler = SYNC_HANDLERS.get(row['entity_type'])

            if not handler:
                # Unknown entity type - mark as failed
                await conn.execute("""
                    UPDATE sync_queue
                    SET status = 'failed',
                        error_msg = $1,
                        attempts = attempts + 1
                    WHERE id = $2
                """, f"No handler for entity_type: {row['entity_type']}", row['id'])
                continue

            try:
                # Execute handler (parse JSON payload)
                payload = json.loads(row['payload']) if isinstance(row['payload'], str) else row['payload']
                await handler(neo4j_driver, payload)

                # Mark as completed
                await conn.execute("""
                    UPDATE sync_queue
                    SET status = 'completed',
                        completed_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, row['id'])

            except Exception as e:
                # Increment attempts, mark as failed if max attempts reached
                new_attempts = row['attempts'] + 1
                new_status = 'failed' if new_attempts >= 3 else 'pending'

                await conn.execute("""
                    UPDATE sync_queue
                    SET attempts = $1,
                        status = $2,
                        error_msg = $3
                    WHERE id = $4
                """, new_attempts, new_status, str(e), row['id'])

                # Create alert if final failure
                if new_status == 'failed':
                    from monitoring.alerts import alert_sync_failure
                    await alert_sync_failure(conn, row['id'], str(e))

                print(f"Sync failed for {row['entity_type']} {row['entity_id']}: {e}")

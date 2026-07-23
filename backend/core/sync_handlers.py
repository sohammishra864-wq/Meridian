"""Sync handlers - Postgres → Neo4j synchronization."""

from neo4j import AsyncDriver


async def sync_company_to_neo4j(driver: AsyncDriver, payload: dict) -> None:
    """Sync company to Neo4j. Idempotent via MERGE."""
    async with driver.session() as session:
        await session.run("""
            MERGE (c:Company {pg_id: $pg_id})
            SET c.canonical_name = $canonical_name,
                c.ticker = $ticker,
                c.lei = $lei,
                c.cik = $cik,
                c.updated_at = datetime()
        """, payload)


async def sync_person_to_neo4j(driver: AsyncDriver, payload: dict) -> None:
    """Sync person to Neo4j. Idempotent via MERGE."""
    async with driver.session() as session:
        await session.run("""
            MERGE (p:Person {pg_id: $pg_id})
            SET p.full_name = $full_name,
                p.updated_at = datetime()
        """, payload)


async def sync_country_to_neo4j(driver: AsyncDriver, payload: dict) -> None:
    """Sync country to Neo4j. Idempotent via MERGE."""
    async with driver.session() as session:
        await session.run("""
            MERGE (c:Country {iso_alpha2: $iso_alpha2})
            SET c.name = $name,
                c.region = $region,
                c.updated_at = datetime()
        """, payload)

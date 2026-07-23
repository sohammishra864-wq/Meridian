"""Neo4j schema initialization - constraints and indexes."""

from neo4j import AsyncDriver

CYPHER_CONSTRAINTS = [
    "CREATE CONSTRAINT company_pg_id IF NOT EXISTS FOR (c:Company) REQUIRE c.pg_id IS UNIQUE",
    "CREATE CONSTRAINT person_pg_id IF NOT EXISTS FOR (p:Person) REQUIRE p.pg_id IS UNIQUE",
    "CREATE CONSTRAINT country_iso IF NOT EXISTS FOR (c:Country) REQUIRE c.iso_alpha2 IS UNIQUE",
    "CREATE CONSTRAINT industry_gics IF NOT EXISTS FOR (i:Industry) REQUIRE i.gics_code IS UNIQUE",
    "CREATE CONSTRAINT fund_pg_id IF NOT EXISTS FOR (f:Fund) REQUIRE f.pg_id IS UNIQUE",
    # ponytail: NOT NULL constraint requires Neo4j Enterprise - application enforces this
]

CYPHER_INDEXES = [
    "CREATE INDEX company_ticker IF NOT EXISTS FOR (c:Company) ON (c.ticker)",
    "CREATE INDEX company_name_idx IF NOT EXISTS FOR (c:Company) ON (c.canonical_name)",
    "CREATE INDEX company_cik IF NOT EXISTS FOR (c:Company) ON (c.cik)",
]


async def initialize_neo4j_schema(driver: AsyncDriver) -> None:
    """Initialize Neo4j schema: constraints, indexes. Idempotent."""
    async with driver.session() as session:
        for cypher in CYPHER_CONSTRAINTS + CYPHER_INDEXES:
            await session.run(cypher)

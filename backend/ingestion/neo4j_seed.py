"""Neo4j graph seeding: GICS competitors, countries, persons."""
from neo4j import AsyncGraphDatabase
from typing import List, Tuple


async def seed_gics_competitors(neo4j_driver, company_id: int, company_neo4j_id: str, industry_id: str, company_name: str) -> int:
    """
    Create COMPETES_WITH edges to all companies in same GICS industry.
    Returns count of edges created.
    """
    async with neo4j_driver.session() as session:
        # Find all companies in same GICS industry
        result = await session.run("""
            MATCH (c:Company)
            WHERE c.gics_code = $industry_id
              AND c.company_id <> $company_id
            RETURN c.company_id as competitor_id, c.name as competitor_name
        """, industry_id=industry_id, company_id=company_id)

        competitors = [dict(r) async for r in result]

        if not competitors:
            return 0

        # Create COMPETES_WITH edges (symmetric)
        for comp in competitors:
            await session.run("""
                MATCH (a:Company {company_id: $company_id})
                MATCH (b:Company {company_id: $competitor_id})
                MERGE (a)-[r:COMPETES_WITH {
                    confidence: 0.50,
                    source_basis: 'gics_same_industry',
                    market_segment: $industry_id,
                    confirmed: false
                }]->(b)
                MERGE (b)-[r2:COMPETES_WITH {
                    confidence: 0.50,
                    source_basis: 'gics_same_industry',
                    market_segment: $industry_id,
                    confirmed: false
                }]->(a)
            """, company_id=company_id, competitor_id=comp['competitor_id'], industry_id=industry_id)

        return len(competitors)


async def seed_countries(neo4j_driver, countries: List[Tuple[str, str, str]]) -> int:
    """
    Seed country nodes from PostgreSQL countries table.
    Input: [(iso_alpha2, name, region), ...]
    Returns count of nodes created.
    """
    async with neo4j_driver.session() as session:
        count = 0
        for iso, name, region in countries:
            await session.run("""
                MERGE (c:Country {iso_alpha2: $iso})
                ON CREATE SET c.name = $name, c.region = $region
            """, iso=iso, name=name, region=region)
            count += 1
        return count


async def create_person_node(neo4j_driver, person_id: int, full_name: str, nationality: str = None) -> None:
    """Create person node in Neo4j."""
    async with neo4j_driver.session() as session:
        await session.run("""
            MERGE (p:Person {person_id: $person_id})
            ON CREATE SET p.full_name = $full_name, p.nationality = $nationality
        """, person_id=person_id, full_name=full_name, nationality=nationality)


async def create_person_role_edge(
    neo4j_driver,
    person_id: int,
    company_id: int,
    role_type: str,
    title: str = None
) -> None:
    """
    Create person → company relationship edge.
    role_type: 'executive', 'board_member', 'founder'
    """
    async with neo4j_driver.session() as session:
        if role_type == 'board_member':
            edge_type = 'SITS_ON_BOARD'
        elif role_type == 'founder':
            edge_type = 'FOUNDED'
        else:
            edge_type = 'SERVES_AS'

        await session.run(f"""
            MATCH (p:Person {{person_id: $person_id}})
            MATCH (c:Company {{company_id: $company_id}})
            MERGE (p)-[r:{edge_type}]->(c)
            ON CREATE SET r.title = $title, r.role_type = $role_type
        """, person_id=person_id, company_id=company_id, title=title, role_type=role_type)

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from core.database import get_db
import asyncpg
import os
from neo4j import AsyncGraphDatabase

router = APIRouter(tags=["graph"])

# ponytail: global Neo4j driver, initialized by main.py
_neo4j_driver = None


def set_neo4j_driver(driver):
    global _neo4j_driver
    _neo4j_driver = driver


def get_neo4j():
    if not _neo4j_driver:
        raise HTTPException(500, "Neo4j driver not initialized")
    return _neo4j_driver


@router.get("/graph/company/{company_id}/context")
async def get_company_graph_context(
    company_id: int,
    neo4j = Depends(get_neo4j)
):
    """
    Get graph context for a company: competitors, subsidiaries, people.
    Returns GraphNode/GraphEdge JSON.
    """
    async with neo4j.session() as session:
        # Get competitors (1-hop COMPETES_WITH)
        result = await session.run("""
            MATCH (c:Company {company_id: $company_id})-[r:COMPETES_WITH]->(comp:Company)
            RETURN comp.company_id as id,
                   comp.name as name,
                   r.confidence as confidence,
                   r.source_basis as source_basis,
                   r.market_segment as market_segment,
                   r.confirmed as confirmed
            LIMIT 50
        """, company_id=company_id)

        competitors = []
        async for record in result:
            competitors.append({
                "id": record["id"],
                "name": record["name"],
                "confidence": record["confidence"],
                "source_basis": record["source_basis"],
                "market_segment": record["market_segment"],
                "confirmed": record["confirmed"]
            })

        # Get person relationships
        result = await session.run("""
            MATCH (p:Person)-[r]->(c:Company {company_id: $company_id})
            WHERE type(r) IN ['SERVES_AS', 'SITS_ON_BOARD', 'FOUNDED']
            RETURN p.person_id as person_id,
                   p.full_name as name,
                   type(r) as relationship_type,
                   r.title as title
            LIMIT 20
        """, company_id=company_id)

        people = []
        async for record in result:
            people.append({
                "person_id": record["person_id"],
                "name": record["name"],
                "relationship_type": record["relationship_type"],
                "title": record["title"]
            })

        return {
            "company_id": company_id,
            "competitors": competitors,
            "people": people
        }


@router.post("/graph/edges/{edge_id}/confirm")
async def confirm_edge(
    edge_id: str,
    neo4j = Depends(get_neo4j)
):
    """
    Analyst confirmation: upgrade edge confidence from 0.50 to 0.85.
    """
    # ponytail: edge_id format: "company_a_id:company_b_id:COMPETES_WITH"
    parts = edge_id.split(":")
    if len(parts) != 3:
        raise HTTPException(400, "Invalid edge_id format")

    company_a_id = int(parts[0])
    company_b_id = int(parts[1])
    edge_type = parts[2]

    async with neo4j.session() as session:
        await session.run(f"""
            MATCH (a:Company {{company_id: $company_a_id}})-[r:{edge_type}]->(b:Company {{company_id: $company_b_id}})
            SET r.confidence = 0.85,
                r.confirmed = true,
                r.confirmed_at = datetime()
        """, company_a_id=company_a_id, company_b_id=company_b_id)

        # Update symmetric edge
        await session.run(f"""
            MATCH (b:Company {{company_id: $company_b_id}})-[r:{edge_type}]->(a:Company {{company_id: $company_a_id}})
            SET r.confidence = 0.85,
                r.confirmed = true,
                r.confirmed_at = datetime()
        """, company_a_id=company_a_id, company_b_id=company_b_id)

    return {"status": "confirmed", "edge_id": edge_id, "new_confidence": 0.85}


@router.get("/graph/company/{company_id}/subsidiaries")
async def get_subsidiary_tree(
    company_id: int,
    max_depth: int = 10,
    neo4j = Depends(get_neo4j)
):
    """Get full subsidiary tree using variable-length path query."""
    async with neo4j.session() as session:
        result = await session.run("""
            MATCH path = (child:Company)-[:SUBSIDIARY_OF*1..{max_depth}]->(parent:Company {company_id: $company_id})
            RETURN child.company_id as subsidiary_id,
                   child.name as subsidiary_name,
                   length(path) as depth
        """.replace("{max_depth}", str(max_depth)), company_id=company_id)

        subsidiaries = []
        async for record in result:
            subsidiaries.append({
                "subsidiary_id": record["subsidiary_id"],
                "name": record["subsidiary_name"],
                "depth": record["depth"]
            })

        return {
            "company_id": company_id,
            "subsidiaries": subsidiaries
        }

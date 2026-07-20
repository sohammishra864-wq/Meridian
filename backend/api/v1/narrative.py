"""Narrative generation API - Epic 5b."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.database import get_db
import asyncpg
import re
import os
from intelligence.llm_provider import AnthropicProvider, MockProvider


router = APIRouter(tags=["narrative"])


class NarrativeRequest(BaseModel):
    company_id: int


class NarrativeResponse(BaseModel):
    company_id: int
    company_name: str
    narrative: str
    source_count: int  # number of [SOURCE] tags found


# ponytail: global provider, initialized once
_provider = None


def get_provider():
    global _provider
    if not _provider:
        # Use mock provider if ANTHROPIC_API_KEY not set (for tests/dev)
        api_key = os.getenv('ANTHROPIC_API_KEY')
        _provider = AnthropicProvider(api_key) if api_key else MockProvider()
    return _provider


@router.post("/narrative", response_model=NarrativeResponse)
async def generate_narrative(
    request: NarrativeRequest,
    db: asyncpg.Connection = Depends(get_db)
):
    """
    Generate AI narrative for a company.
    User-triggered, on-demand only (not automated).
    """
    company_id = request.company_id

    # Get company info
    company = await db.fetchrow("""
        SELECT e.canonical_name, c.ticker
        FROM companies c
        JOIN entity_master e ON c.entity_master_id = e.id
        WHERE c.id = $1
    """, company_id)

    if not company:
        raise HTTPException(404, "Company not found")

    # Get latest metrics
    metrics = await db.fetch("""
        SELECT metric_type, value, unit, source_filing_id, xbrl_concepts_used
        FROM metrics
        WHERE company_id = $1 AND superseded_at IS NULL
        ORDER BY valid_to DESC
        LIMIT 10
    """, company_id)

    # Get risks
    risks = await db.fetch("""
        SELECT risk_type, severity, description, source_basis
        FROM risks
        WHERE company_id = $1 AND (valid_to IS NULL OR valid_to >= CURRENT_DATE)
        ORDER BY created_at DESC
        LIMIT 5
    """, company_id)

    # Get fragility score
    fragility = await db.fetchrow("""
        SELECT score, breakdown
        FROM fragility_scores
        WHERE company_id = $1
        ORDER BY computed_at DESC
        LIMIT 1
    """, company_id)

    # Build context
    context = {
        'company_name': company['canonical_name'],
        'ticker': company['ticker'],
        'metrics': [dict(m) for m in metrics],
        'risks': [dict(r) for r in risks],
        'fragility_score': fragility['score'] if fragility else None
    }

    # Generate narrative
    provider = get_provider()
    prompt = f"Generate a 3-paragraph financial analysis for {company['canonical_name']} ({company['ticker']}) based on the provided metrics and risks."

    narrative_text = await provider.generate(prompt, context)

    # Validate [SOURCE] tags present
    source_tags = re.findall(r'\[SOURCE:[^\]]+\]', narrative_text)

    if len(source_tags) == 0:
        raise HTTPException(
            500,
            "Narrative generation failed: no [SOURCE] tags found. LLM must cite sources."
        )

    # Validate no Buy/Sell/Hold recommendations
    forbidden_words = ['buy', 'sell', 'hold', 'strong buy', 'overweight', 'underweight']
    narrative_lower = narrative_text.lower()

    for word in forbidden_words:
        if word in narrative_lower:
            raise HTTPException(
                500,
                f"Narrative contains forbidden recommendation: '{word}'. Investment decisions require human judgment."
            )

    return {
        'company_id': company_id,
        'company_name': company['canonical_name'],
        'narrative': narrative_text,
        'source_count': len(source_tags)
    }

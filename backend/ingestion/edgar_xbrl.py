from datetime import date, datetime
from typing import Optional
import httpx
from calculation.validation import validate_xbrl_facts
from calculation.confidence import compute_metric_confidence


async def fetch_company_facts(cik: str) -> Optional[dict]:
    """Fetch XBRL Company Facts from SEC EDGAR API."""
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json"
    headers = {"User-Agent": "Meridian Platform research@meridian.ai"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            return None


def extract_xbrl_facts(company_facts: dict, filing_date: date) -> dict:
    """
    Extract relevant XBRL facts for calculation engine.
    Returns dict with standardized keys.
    """
    facts = company_facts.get("facts", {}).get("us-gaap", {})

    # ponytail: direct key extraction, try both USD and shares units
    def val(concept: str, unit: str = "USD") -> float:
        fact = facts.get(concept, {}).get("units", {}).get(unit, [])
        if not fact:
            return 0.0
        # Get most recent value as of filing_date
        relevant = [f for f in fact if f.get("end", "") <= str(filing_date)]
        return float(relevant[-1].get("val", 0)) if relevant else 0.0

    return {
        "Revenue": val("Revenues"),
        "Assets": val("Assets"),
        "Liabilities": val("Liabilities"),
        "CashAndCashEquivalents": val("CashAndCashEquivalents"),
        "CommonStockSharesOutstanding": val("CommonStockSharesOutstanding", "shares"),
        "GrossProfit": val("GrossProfit"),
        "CostOfRevenue": val("CostOfRevenue"),
        "OperatingIncome": val("OperatingIncomeLoss"),
        "LongTermDebt": val("LongTermDebt"),
        "ShortTermDebt": val("ShortTermDebtCurrent"),
        "NetCashProvidedByUsedInOperatingActivities": val("NetCashProvidedByUsedInOperatingActivities"),
        "PaymentsToAcquirePropertyPlantAndEquipment": val("PaymentsToAcquirePropertyPlantAndEquipment"),
    }


async def ingest_xbrl_for_company(
    company_id: int,
    cik: str,
    filing_date: date,
) -> tuple[bool, dict, list[str]]:
    """
    Ingest XBRL data for a company.
    Returns: (success, validated_facts, error_messages)
    """
    company_facts = await fetch_company_facts(cik)
    if not company_facts:
        return False, {}, ["Failed to fetch XBRL data from SEC"]

    facts = extract_xbrl_facts(company_facts, filing_date)
    is_valid, messages, confidence_mult = validate_xbrl_facts(facts)

    if not is_valid:
        return False, facts, messages

    return True, facts, messages

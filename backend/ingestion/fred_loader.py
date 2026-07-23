from typing import Optional
import httpx


async def fetch_risk_free_rate() -> Optional[float]:
    """
    Fetch 10-year Treasury rate from FRED API.
    ponytail: no API key needed for this endpoint, returns latest value
    """
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=2024-01-01"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            lines = response.text.strip().split('\n')
            # Last line: date,value
            last = lines[-1].split(',')
            return float(last[1]) / 100  # Convert percentage to decimal
    except (httpx.HTTPError, ValueError, IndexError):
        return 0.04  # ponytail: fallback to 4% if FRED unavailable

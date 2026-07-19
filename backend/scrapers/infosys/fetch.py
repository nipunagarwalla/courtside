"""HTTP layer for the Infosys ATP API — fetch + decrypt."""
import httpx

from .config import INFOSYS_HOST, HEADERS, ENDPOINTS
from .decrypt import decrypt_infosys_response


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(http2=True, headers=HEADERS, timeout=20)


async def fetch_endpoint(
    client: httpx.AsyncClient, endpoint: str, year: int | str,
    event_id: str, match_id: str,
) -> dict | None:
    """Fetch one Infosys endpoint and return the decrypted payload.

    Returns None on 404 (no data for this match) or any other failure.
    """
    url = INFOSYS_HOST + ENDPOINTS[endpoint].format(
        year=year, event_id=event_id, match_id=match_id
    )
    try:
        r = await client.get(url)
        if r.status_code != 200:
            return None
        return decrypt_infosys_response(r.json())
    except Exception as e:
        print(f"  infosys fetch error {endpoint} {match_id}: {e}")
        return None

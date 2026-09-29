"""Client for the partner bank's API (see bank_mock/)."""

import httpx

from core.config import settings


class BankUnavailable(Exception):
    pass


def get_client() -> httpx.Client:
    """Overridable in tests to point at an in-process bank app."""
    return httpx.Client(
        base_url=settings.bank_api_url, timeout=settings.bank_timeout_seconds
    )


def request_preapproval(payload: dict) -> dict:
    try:
        with get_client() as client:
            resp = client.post(
                "/v1/preapproved-offers",
                json=payload,
                headers={"X-API-Key": settings.bank_api_key},
            )
    except httpx.HTTPError as exc:
        raise BankUnavailable("bank service is unreachable") from exc
    if resp.status_code != 200:
        raise BankUnavailable(f"bank service returned {resp.status_code}")
    return resp.json()

import httpx

from app.config import settings


def get_reservation_by_qr(qr_code: str) -> dict | None:
    """ticket-service에 QR 코드로 예매 건을 조회한다 (FR-010)."""
    try:
        response = httpx.get(
            f"{settings.ticket_service_url}/api/reservations/qr/{qr_code}",
            headers={"X-Internal-Api-Key": settings.internal_api_key},
            timeout=3.0,
        )
    except httpx.HTTPError:
        return None

    if response.status_code != 200:
        return None
    return response.json()

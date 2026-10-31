"""Optional shared-secret authentication.

Every task endpoint can start a real browser and spend LLM credits, so anything
reachable beyond localhost should not be open to the world. Set ``API_KEY`` in
``backend/.env`` to require it; leave it blank (the default) for local
development, where the check is skipped.

HTTP clients send the key in the ``X-API-Key`` header. Browsers cannot set
headers on a WebSocket handshake, so the socket takes it as ``?api_key=``.
"""

import secrets
from typing import Optional

from fastapi import Header, HTTPException, WebSocket, status

from app.config import get_settings


def is_valid_key(provided: Optional[str]) -> bool:
    expected = get_settings().api_key
    if not expected:
        return True
    if not provided:
        return False
    return secrets.compare_digest(provided.encode(), expected.encode())


async def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """FastAPI dependency for HTTP routes."""
    if not is_valid_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )


def websocket_authorized(websocket: WebSocket) -> bool:
    return is_valid_key(websocket.query_params.get("api_key"))

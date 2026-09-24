"""Customer identity for the support API.

Confirmed against the real Tasseer backend (api.ksatasseerltdapi.com,
application/controllers/api/Users.php + application/libraries/
Authorization_Token.php): customers already carry a long-lived HS256 JWT
(`{id, username, user_type, time}`, ~360 day expiry, no server-side
revocation list) that they send as a RAW `Authorization` header value on
every API call - `Authorization_Token::validateToken()` passes the header
straight to `JWT::decode()` with no `Bearer ` stripping, and the app's own
`ApiClient` (composeApp/.../data/remote/ApiClient.kt) sends it the same way:
`header("Authorization", authToken)`, no scheme prefix. There is no separate
sessions/tokens table this service could read instead.

So the in-app chat screen sends that SAME raw token, and this service
verifies it by calling the existing, already-authenticated `GET /api/user/en`
endpoint on the main API (Users.php::user_get) rather than decoding the JWT
itself. Two reasons this beats decoding locally:
  - no need to share the PHP app's JWT signing secret with a new service
  - `user_get` re-reads the live `users` row, so a deactivated account
    (`is_active = 0`) is caught even though `validateToken()` on the PHP
    side alone would still accept an old, still-unexpired token for it
"""

from __future__ import annotations

import time

import httpx
from fastapi import Header, HTTPException, status

from app.core.config import settings


class SupportIdentity:
    def __init__(self, customer_id: int, name: str):
        self.customer_id = customer_id
        self.name = name


# Tiny in-memory TTL cache so a back-and-forth chat doesn't re-hit the main
# API on every single message. Not shared across processes - fine for a
# single-instance MVP, swap for Redis if this scales out.
_cache: dict[str, tuple[float, SupportIdentity]] = {}
_CACHE_TTL_SECONDS = 60


async def verify_handoff_token(authorization: str = Header(default="")) -> SupportIdentity:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()

    cached = _cache.get(token)
    if cached and cached[0] > time.time():
        return cached[1]

    url = f"{settings.tasseer_api_base_url.rstrip('/')}/api/user/en"
    async with httpx.AsyncClient(timeout=10) as client:
        # Raw token, no "Bearer " prefix - the PHP JWT decoder reads this
        # header value directly (see module docstring). Re-adding "Bearer "
        # here was the actual bug that made every real session look invalid.
        resp = await client.get(url, headers={"Authorization": token})

    if resp.status_code != 200:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not verify session")

    body = resp.json()
    if not body.get("status") or not body.get("data"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")

    data = body["data"]
    identity = SupportIdentity(customer_id=int(data["id"]), name=data.get("name", ""))
    _cache[token] = (time.time() + _CACHE_TTL_SECONDS, identity)
    return identity

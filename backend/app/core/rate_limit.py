"""Simple in-memory rate limiter for auth endpoints.

For production, use Redis-backed rate limiting (e.g. slowapi with Redis).
"""

import time
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

# (ip, path) -> (request_count, window_start)
_rate_store: Dict[Tuple[str, str], Tuple[int, float]] = defaultdict(lambda: (0, 0.0))

MAX_REQUESTS = 10
WINDOW_SECONDS = 60

RATE_LIMITED_PATHS = {"/api/v1/auth/token", "/api/v1/auth/register"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path not in RATE_LIMITED_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = (client_ip, path)
        now = time.time()

        count, window_start = _rate_store[key]
        if now - window_start > WINDOW_SECONDS:
            _rate_store[key] = (1, now)
        else:
            count += 1
            if count > MAX_REQUESTS:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Try again later."},
                )
            _rate_store[key] = (count, window_start)

        return await call_next(request)

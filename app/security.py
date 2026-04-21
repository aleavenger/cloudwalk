from __future__ import annotations

from fastapi import Header, HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware


class MonitorPayloadLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/monitor":
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_bytes:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Payload too large")
            body = await request.body()
            if len(body) > self.max_bytes:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Payload too large")
            request._body = body
        return await call_next(request)


def build_api_key_guard(expected_key: str | None):
    async def _require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
        if not expected_key:
            return
        if x_api_key != expected_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return _require_api_key

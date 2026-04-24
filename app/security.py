from __future__ import annotations

from secrets import compare_digest

from fastapi import Header, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers


class MonitorPayloadLimitMiddleware:
    _TARGET_PATHS = {"/monitor", "/monitor/transaction"}

    def __init__(self, app, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "").upper()
        if method != "POST" or path not in self._TARGET_PATHS:
            await self.app(scope, receive, send)
            return

        headers = Headers(raw=scope.get("headers", []))
        content_length = headers.get("content-length")
        if content_length is not None:
            try:
                parsed_content_length = int(content_length)
                if parsed_content_length < 0:
                    raise ValueError
            except ValueError:
                await self._send_error(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Invalid content-length",
                    scope=scope,
                    receive=receive,
                    send=send,
                )
                return
            if parsed_content_length > self.max_bytes:
                await self._send_error(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="Payload too large",
                    scope=scope,
                    receive=receive,
                    send=send,
                )
                return

        seen_bytes = 0
        buffered_messages = []
        while True:
            message = await receive()
            if message.get("type") != "http.request":
                buffered_messages.append(message)
                if message.get("type") == "http.disconnect":
                    break
                continue

            chunk = message.get("body", b"")
            seen_bytes += len(chunk)
            if seen_bytes > self.max_bytes:
                await self._send_error(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="Payload too large",
                    scope=scope,
                    receive=receive,
                    send=send,
                )
                return

            buffered_messages.append(message)
            if not message.get("more_body", False):
                break

        next_message_index = 0

        async def replay_receive():
            nonlocal next_message_index
            if next_message_index < len(buffered_messages):
                buffered = buffered_messages[next_message_index]
                next_message_index += 1
                return buffered
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)

    async def _send_error(
        self,
        *,
        status_code: int,
        detail: str,
        scope,
        receive,
        send,
    ) -> None:
        response = JSONResponse(status_code=status_code, content={"detail": detail})
        await response(scope, receive, send)


def build_api_key_guard(expected_key: str | None):
    async def _require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
        if not expected_key:
            return
        if x_api_key is None or not compare_digest(x_api_key, expected_key):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return _require_api_key

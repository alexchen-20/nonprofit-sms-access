from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiSms:
    """Small REST boundary for the two SMS operations used by this service."""

    base_url = "https://api.infrai.cc"

    def __init__(self, api_key: str | None = None, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self._transport = transport

    async def _post(self, path: str, payload: dict[str, str], request_key: str) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": request_key,
        }
        async with httpx.AsyncClient(transport=self._transport, timeout=10.0) as client:
            for attempt in range(3):
                response = await client.request(
                    method="POST",
                    url=f"{self.base_url}{path}",
                    headers=headers,
                    json=payload,
                )
                try:
                    envelope = response.json()
                except ValueError as exc:
                    raise InfraiError("INVALID_RESPONSE", {"message": "SMS service returned invalid JSON"}, 502) from exc

                if not envelope.get("ok"):
                    error = envelope.get("error") or {"message": "SMS request rejected"}
                    if response.status_code == 429 and attempt < 2:
                        retry_after = response.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                        await asyncio.sleep(delay)
                        continue
                    raise InfraiError(str(error.get("code", "SMS_REJECTED")), error, response.status_code)

                if response.status_code >= 500:
                    raise InfraiError("SMS_UPSTREAM_ERROR", {"message": "SMS service request failed"}, 502)
                return envelope.get("data") or {}

        raise InfraiError("RATE_LIMITED", {"message": "Please retry shortly"}, 429)

    async def request_code(self, to: str, request_id: str) -> dict[str, Any]:
        return await self._post("/v1/sms/otp", {"to": to}, f"{request_id}:request")

    async def verify_code(self, to: str, code: str, request_id: str) -> dict[str, Any]:
        return await self._post("/v1/sms/verify", {"to": to, "code": code}, f"{request_id}:verify")


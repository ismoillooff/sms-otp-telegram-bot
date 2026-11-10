"""SMS senders: console (development) and SMSXabarnoma.uz (production)."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Protocol

import aiohttp

logger = logging.getLogger(__name__)


class SmsError(Exception):
    pass


_STATUS_HINTS = {
    400: "bad request or blocked content (CONTENT_BLOCKED) - check phone / SMS_TEMPLATE",
    401: "API key missing or invalid - check SMSX_API_KEY",
    402: "insufficient balance (INSUFFICIENT_BALANCE) or key subscription unpaid",
    403: "key lacks 'send' scope, IP not allowed, or account blocked",
    429: "key daily/monthly limit reached or too many requests",
}


def _describe_error(status: int, body: Any) -> str:
    hint = _STATUS_HINTS.get(status, "unexpected error")
    return f"HTTP {status} ({hint}): {body}"


class SmsSender(Protocol):
    async def send(self, phone: str, text: str) -> None: ...

    async def close(self) -> None: ...


class ConsoleSmsSender:
    """Logs the SMS instead of sending it. For local testing without spending money."""

    async def send(self, phone: str, text: str) -> None:
        logger.warning("[CONSOLE SMS] to +%s: %s", phone, text)

    async def close(self) -> None:
        return None


class SmsXabarnomaSender:
    """SMSXabarnoma.uz REST API client.

    POST {base}/sms/send  {"phone": "998901234567", "text": "...", "externalId"?: "..."}
    Auth: X-API-Key: sk_...
    Retries on network errors reuse the same Idempotency-Key, so the SMS is never
    sent (or charged) twice.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://smsxabarnoma.uz/api/v1",
        callback_url: str | None = None,
        retries: int = 2,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._callback_url = callback_url or None
        self._retries = retries
        self._session: aiohttp.ClientSession | None = None

    def _http(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"X-API-Key": self._api_key, "Accept": "application/json"},
            )
        return self._session

    async def _request(self, method: str, path: str, **kwargs: Any) -> tuple[int, Any]:
        async with self._http().request(method, f"{self._base_url}{path}", **kwargs) as resp:
            try:
                body = await resp.json(content_type=None)
            except ValueError:
                body = await resp.text()
            return resp.status, body

    async def send(self, phone: str, text: str) -> None:
        idempotency_key = str(uuid.uuid4())
        payload: dict[str, str] = {"phone": phone, "text": text, "externalId": idempotency_key}
        if self._callback_url:
            payload["callbackUrl"] = self._callback_url

        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                status, body = await self._request(
                    "POST",
                    "/sms/send",
                    json=payload,
                    headers={"Idempotency-Key": idempotency_key},
                )
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_error = exc
                logger.warning("SMSXabarnoma network error (attempt %s): %s", attempt + 1, exc)
                await asyncio.sleep(1 + attempt)
                continue

            if 200 <= status < 300:
                info = body if isinstance(body, dict) else {}
                sms_status = info.get("status")
                logger.info(
                    "SMS accepted for +%s: id=%s status=%s parts=%s cost=%s duplicate=%s",
                    phone, info.get("id"), sms_status, info.get("parts"),
                    info.get("cost"), info.get("duplicate"),
                )
                if sms_status == "PENDING_REVIEW":
                    logger.warning(
                        "SMS %s is under moderation (PENDING_REVIEW) - delivery may be delayed. "
                        "Consider adjusting SMS_TEMPLATE.", info.get("id"),
                    )
                elif sms_status == "FAILED":
                    raise SmsError(f"SMSXabarnoma rejected SMS: {body}")
                return
            if status >= 500 and attempt < self._retries:
                logger.warning("SMSXabarnoma %s (attempt %s): %s", status, attempt + 1, body)
                await asyncio.sleep(1 + attempt)
                continue
            raise SmsError(f"SMSXabarnoma send failed: {_describe_error(status, body)}")

        raise SmsError(f"SMSXabarnoma unreachable: {last_error}")

    async def balance(self) -> Any:
        """GET /balance — used on startup to validate the API key."""
        try:
            status, body = await self._request("GET", "/balance")
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise SmsError(f"SMSXabarnoma unreachable: {exc}") from exc
        if status != 200:
            raise SmsError(f"SMSXabarnoma balance check failed: {_describe_error(status, body)}")
        return body

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

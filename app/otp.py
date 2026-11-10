"""One-time password generation, storage and verification (in memory)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class ResendCooldown(Exception):
    def __init__(self, seconds_left: int) -> None:
        super().__init__(f"Resend available in {seconds_left}s")
        self.seconds_left = seconds_left


class SendLimitExceeded(Exception):
    pass


class VerifyStatus(Enum):
    OK = "ok"
    WRONG = "wrong"
    EXPIRED = "expired"
    LOCKED = "locked"
    NO_SESSION = "no_session"


@dataclass(slots=True)
class VerifyResult:
    status: VerifyStatus
    attempts_left: int = 0
    phone: str | None = None


@dataclass(slots=True)
class _OtpSession:
    phone: str
    code_hash: bytes
    expires_at: float
    attempts_left: int


HOUR = 3600


class OtpService:
    def __init__(
        self,
        *,
        length: int = 6,
        ttl: int = 300,
        max_attempts: int = 3,
        resend_cooldown: int = 60,
        max_sends_per_hour: int = 5,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.length = length
        self.ttl = ttl
        self.max_attempts = max_attempts
        self.resend_cooldown = resend_cooldown
        self.max_sends_per_hour = max_sends_per_hour
        self._clock = clock
        self._key = secrets.token_bytes(32)
        self._sessions: dict[int, _OtpSession] = {}
        self._sends: dict[int, deque[float]] = {}

    def _hash(self, code: str) -> bytes:
        return hmac.new(self._key, code.encode(), hashlib.sha256).digest()

    def _recent_sends(self, user_id: int) -> deque[float]:
        now = self._clock()
        sends = self._sends.setdefault(user_id, deque())
        while sends and now - sends[0] >= HOUR:
            sends.popleft()
        return sends

    def seconds_until_resend(self, user_id: int) -> int:
        sends = self._recent_sends(user_id)
        if not sends:
            return 0
        left = self.resend_cooldown - (self._clock() - sends[-1])
        return max(0, int(left + 0.999))

    def issue(self, user_id: int, phone: str) -> str:
        """Create a new code for the user. Raises ResendCooldown / SendLimitExceeded."""
        wait = self.seconds_until_resend(user_id)
        if wait > 0:
            raise ResendCooldown(wait)
        sends = self._recent_sends(user_id)
        if len(sends) >= self.max_sends_per_hour:
            raise SendLimitExceeded()

        code = f"{secrets.randbelow(10**self.length):0{self.length}d}"
        now = self._clock()
        self._sessions[user_id] = _OtpSession(
            phone=phone,
            code_hash=self._hash(code),
            expires_at=now + self.ttl,
            attempts_left=self.max_attempts,
        )
        sends.append(now)
        return code

    def cancel(self, user_id: int) -> None:
        self._sessions.pop(user_id, None)

    def verify(self, user_id: int, code: str) -> VerifyResult:
        session = self._sessions.get(user_id)
        if session is None:
            return VerifyResult(VerifyStatus.NO_SESSION)
        if self._clock() >= session.expires_at:
            self._sessions.pop(user_id, None)
            return VerifyResult(VerifyStatus.EXPIRED, phone=session.phone)

        if hmac.compare_digest(session.code_hash, self._hash(code)):
            self._sessions.pop(user_id, None)
            return VerifyResult(VerifyStatus.OK, phone=session.phone)

        session.attempts_left -= 1
        if session.attempts_left <= 0:
            self._sessions.pop(user_id, None)
            return VerifyResult(VerifyStatus.LOCKED, phone=session.phone)
        return VerifyResult(VerifyStatus.WRONG, attempts_left=session.attempts_left, phone=session.phone)

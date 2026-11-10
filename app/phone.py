"""Phone number normalization (Uzbekistan, +998)."""

from __future__ import annotations

import re

_UZ_PHONE = re.compile(r"^998\d{9}$")


def normalize_phone(raw: str) -> str | None:
    """Return the phone as 998XXXXXXXXX, or None if it is not a valid Uzbek number."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:  # 901234567 -> 998901234567
        digits = "998" + digits
    return digits if _UZ_PHONE.match(digits) else None


def format_phone(phone: str) -> str:
    """998901234567 -> +998 90 123 45 67"""
    if len(phone) == 12:
        return f"+{phone[:3]} {phone[3:5]} {phone[5:8]} {phone[8:10]} {phone[10:]}"
    return f"+{phone}"

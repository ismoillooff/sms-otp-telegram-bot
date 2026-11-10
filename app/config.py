"""Application settings loaded from environment variables (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str

    # SMS
    sms_provider: str  # "console" | "smsxabarnoma"
    smsx_api_key: str
    smsx_base_url: str
    smsx_callback_url: str
    sms_template: str

    # OTP
    otp_length: int
    otp_ttl: int
    otp_max_attempts: int
    otp_resend_cooldown: int
    otp_max_sends_per_hour: int

    # Storage
    db_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")

        provider = os.getenv("SMS_PROVIDER", "console").strip().lower()
        if provider not in {"console", "smsxabarnoma"}:
            raise RuntimeError("SMS_PROVIDER must be 'console' or 'smsxabarnoma'")

        settings = cls(
            bot_token=token,
            sms_provider=provider,
            smsx_api_key=os.getenv("SMSX_API_KEY", "").strip(),
            smsx_base_url=os.getenv("SMSX_BASE_URL", "https://smsxabarnoma.uz/api/v1").strip(),
            smsx_callback_url=os.getenv("SMSX_CALLBACK_URL", "").strip(),
            sms_template=os.getenv(
                "SMS_TEMPLATE", "Tasdiqlash kodingiz: {code}. Kodni hech kimga bermang."
            ),
            otp_length=_int("OTP_LENGTH", 6),
            otp_ttl=_int("OTP_TTL_SECONDS", 300),
            otp_max_attempts=_int("OTP_MAX_ATTEMPTS", 3),
            otp_resend_cooldown=_int("OTP_RESEND_COOLDOWN_SECONDS", 60),
            otp_max_sends_per_hour=_int("OTP_MAX_SENDS_PER_HOUR", 5),
            db_path=os.getenv("DB_PATH", "bot.db").strip() or "bot.db",
        )

        if provider == "smsxabarnoma" and not settings.smsx_api_key:
            raise RuntimeError("SMSX_API_KEY is required when SMS_PROVIDER=smsxabarnoma")
        if "{code}" not in settings.sms_template:
            raise RuntimeError("SMS_TEMPLATE must contain the {code} placeholder")
        if not 4 <= settings.otp_length <= 8:
            raise RuntimeError("OTP_LENGTH must be between 4 and 8")

        return settings

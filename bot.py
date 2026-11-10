"""Entry point: python bot.py"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import Settings
from app.handlers import router
from app.otp import OtpService
from app.sms import ConsoleSmsSender, SmsError, SmsSender, SmsXabarnomaSender
from app.storage import UserStorage

logger = logging.getLogger("bot")


def build_sms_sender(settings: Settings) -> SmsSender:
    if settings.sms_provider == "smsxabarnoma":
        return SmsXabarnomaSender(
            api_key=settings.smsx_api_key,
            base_url=settings.smsx_base_url,
            callback_url=settings.smsx_callback_url or None,
        )
    logger.warning("SMS_PROVIDER=console: codes are printed to this log, no real SMS is sent")
    return ConsoleSmsSender()


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    settings = Settings.from_env()

    sms = build_sms_sender(settings)
    if isinstance(sms, SmsXabarnomaSender):
        try:
            info = await sms.balance()
            logger.info(
                "SMSXabarnoma: balance=%s %s, price/SMS=%s, scopes=%s",
                info.get("balance"), info.get("currency"), info.get("pricePerSms"), info.get("scopes"),
            )
            if "send" not in (info.get("scopes") or []):
                logger.error("SMSXabarnoma API key has no 'send' scope - SMS will fail")
        except SmsError as exc:
            logger.error("SMSXabarnoma API key check failed: %s", exc)

    users = UserStorage(settings.db_path)
    await users.connect()

    otp = OtpService(
        length=settings.otp_length,
        ttl=settings.otp_ttl,
        max_attempts=settings.otp_max_attempts,
        resend_cooldown=settings.otp_resend_cooldown,
        max_sends_per_hour=settings.otp_max_sends_per_hour,
    )

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage(), otp=otp, sms=sms, users=users, settings=settings)
    dp.include_router(router)

    await bot.set_my_commands([BotCommand(command="start", description="Raqamni tasdiqlash")])
    await bot.set_my_commands(
        [BotCommand(command="start", description="Подтвердить номер")], language_code="ru"
    )

    try:
        logger.info("Bot started")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await sms.close()
        await users.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except RuntimeError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        sys.exit(1)

"""Bot conversation: /start -> phone (contact button) -> SMS code -> verification."""

from __future__ import annotations

import logging
import re

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, User

from app.config import Settings
from app.keyboards import CB_CHANGE, CB_RESEND, code_keyboard, phone_keyboard
from app.otp import OtpService, ResendCooldown, SendLimitExceeded, VerifyStatus
from app.phone import format_phone, normalize_phone
from app.sms import SmsError, SmsSender
from app.states import Verify
from app.storage import UserStorage
from app.texts import detect_lang, t

logger = logging.getLogger(__name__)
router = Router(name="otp")


def _lang(user: User | None) -> str:
    return detect_lang(user.language_code if user else None)


async def _issue_and_send(
    user_id: int, phone: str, otp: OtpService, sms: SmsSender, settings: Settings, lang: str
) -> str | None:
    """Generate a code and send it by SMS. Returns an error text, or None on success."""
    try:
        code = otp.issue(user_id, phone)
    except ResendCooldown as exc:
        return t(lang, "resend_wait", seconds=exc.seconds_left)
    except SendLimitExceeded:
        return t(lang, "send_limit")

    try:
        await sms.send(phone, settings.sms_template.replace("{code}", code))
    except SmsError:
        logger.exception("Failed to send OTP SMS to user %s", user_id)
        otp.cancel(user_id)
        return t(lang, "sms_failed")
    return None


def _code_sent_text(lang: str, phone: str, settings: Settings) -> str:
    return t(
        lang,
        "code_sent",
        phone=format_phone(phone),
        length=settings.otp_length,
        minutes=max(1, settings.otp_ttl // 60),
    )


# ---------- /start ----------


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, otp: OtpService, users: UserStorage) -> None:
    lang = _lang(message.from_user)
    otp.cancel(message.from_user.id)
    await state.clear()
    await state.set_state(Verify.phone)

    verified_phone = await users.get_phone(message.from_user.id)
    if verified_phone:
        text = t(lang, "already_verified", phone=format_phone(verified_phone))
    else:
        text = t(lang, "start", name=message.from_user.first_name or "")
    await message.answer(text, reply_markup=phone_keyboard(lang))


# ---------- Step 1: phone number ----------


async def _accept_phone(
    message: Message,
    phone: str,
    state: FSMContext,
    otp: OtpService,
    sms: SmsSender,
    settings: Settings,
) -> None:
    lang = _lang(message.from_user)
    await message.answer(
        t(lang, "phone_accepted", phone=format_phone(phone)), reply_markup=ReplyKeyboardRemove()
    )

    error = await _issue_and_send(message.from_user.id, phone, otp, sms, settings, lang)
    if error:
        await message.answer(error, reply_markup=phone_keyboard(lang))
        return

    await state.update_data(phone=phone)
    await state.set_state(Verify.code)
    await message.answer(_code_sent_text(lang, phone, settings), reply_markup=code_keyboard(lang))


@router.message(Verify.phone, F.contact)
async def on_contact(
    message: Message, state: FSMContext, otp: OtpService, sms: SmsSender, settings: Settings
) -> None:
    lang = _lang(message.from_user)
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer(t(lang, "not_own_contact"), reply_markup=phone_keyboard(lang))
        return

    phone = normalize_phone(contact.phone_number)
    if phone is None:
        await message.answer(t(lang, "invalid_phone"), reply_markup=phone_keyboard(lang))
        return
    await _accept_phone(message, phone, state, otp, sms, settings)


@router.message(Verify.phone, F.text)
async def on_phone_text(
    message: Message, state: FSMContext, otp: OtpService, sms: SmsSender, settings: Settings
) -> None:
    lang = _lang(message.from_user)
    phone = normalize_phone(message.text)
    if phone is None:
        await message.answer(t(lang, "invalid_phone"), reply_markup=phone_keyboard(lang))
        return
    await _accept_phone(message, phone, state, otp, sms, settings)


@router.message(Verify.phone)
async def on_phone_other(message: Message) -> None:
    lang = _lang(message.from_user)
    await message.answer(t(lang, "use_button"), reply_markup=phone_keyboard(lang))


# ---------- Step 2: verification code ----------


@router.message(Verify.code, F.text)
async def on_code(
    message: Message,
    state: FSMContext,
    otp: OtpService,
    users: UserStorage,
    settings: Settings,
) -> None:
    lang = _lang(message.from_user)
    code = re.sub(r"[\s\-]", "", message.text)
    if not code.isdigit() or len(code) != settings.otp_length:
        await message.answer(t(lang, "code_format", length=settings.otp_length))
        return

    result = otp.verify(message.from_user.id, code)

    if result.status is VerifyStatus.OK:
        user = message.from_user
        await users.save_verified(user.id, result.phone, user.username, user.full_name)
        await state.clear()
        logger.info("User %s verified phone +%s", user.id, result.phone)
        await message.answer(t(lang, "verified", phone=format_phone(result.phone)))
        return

    if result.status is VerifyStatus.WRONG:
        await message.answer(t(lang, "code_wrong", left=result.attempts_left))
        return

    key = {
        VerifyStatus.EXPIRED: "code_expired",
        VerifyStatus.LOCKED: "code_locked",
        VerifyStatus.NO_SESSION: "no_session",
    }[result.status]
    await message.answer(t(lang, key), reply_markup=code_keyboard(lang))


@router.message(Verify.code)
async def on_code_other(message: Message) -> None:
    lang = _lang(message.from_user)
    await message.answer(t(lang, "enter_code"), reply_markup=code_keyboard(lang))


# ---------- Inline buttons ----------


@router.callback_query(Verify.code, F.data == CB_RESEND)
async def on_resend(
    callback: CallbackQuery,
    bot: Bot,
    state: FSMContext,
    otp: OtpService,
    sms: SmsSender,
    settings: Settings,
) -> None:
    lang = _lang(callback.from_user)
    phone = (await state.get_data()).get("phone")
    if not phone:
        await callback.answer(t(lang, "restart"), show_alert=True)
        return

    error = await _issue_and_send(callback.from_user.id, phone, otp, sms, settings, lang)
    if error:
        await callback.answer(error, show_alert=True)
        return

    await callback.answer()
    await bot.send_message(
        callback.from_user.id,
        _code_sent_text(lang, phone, settings),
        reply_markup=code_keyboard(lang),
    )


@router.callback_query(Verify.code, F.data == CB_CHANGE)
async def on_change_phone(
    callback: CallbackQuery, bot: Bot, state: FSMContext, otp: OtpService
) -> None:
    lang = _lang(callback.from_user)
    otp.cancel(callback.from_user.id)
    await state.update_data(phone=None)
    await state.set_state(Verify.phone)
    await callback.answer()
    await bot.send_message(
        callback.from_user.id, t(lang, "use_button"), reply_markup=phone_keyboard(lang)
    )


@router.callback_query(F.data.in_({CB_RESEND, CB_CHANGE}))
async def on_stale_button(callback: CallbackQuery) -> None:
    await callback.answer(t(_lang(callback.from_user), "restart"), show_alert=True)


# ---------- Anything else ----------


@router.message()
async def on_any(message: Message) -> None:
    await message.answer(t(_lang(message.from_user), "restart"))

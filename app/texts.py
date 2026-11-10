"""User-facing texts (uz / ru)."""

from __future__ import annotations

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "start": (
            "Assalomu alaykum, <b>{name}</b>! 👋\n\n"
            "Telefon raqamingizni tasdiqlash uchun pastdagi "
            "<b>«📱 Raqamni yuborish»</b> tugmasini bosing."
        ),
        "already_verified": (
            "✅ Raqamingiz allaqachon tasdiqlangan: <b>{phone}</b>\n\n"
            "Boshqa raqamni tasdiqlash uchun pastdagi tugmani bosing."
        ),
        "btn_send_phone": "📱 Raqamni yuborish",
        "btn_resend": "🔄 Kodni qayta yuborish",
        "btn_change": "✏️ Raqamni o'zgartirish",
        "phone_placeholder": "Tugmani bosing",
        "code_placeholder": "Kodni kiriting",
        "not_own_contact": "❗️ Iltimos, faqat <b>o'zingizning</b> raqamingizni tugma orqali yuboring.",
        "invalid_phone": (
            "❗️ Raqam noto'g'ri. Pastdagi tugma orqali yuboring yoki "
            "<code>+998901234567</code> formatida yozing."
        ),
        "phone_accepted": "📨 Raqam qabul qilindi: <b>{phone}</b>",
        "code_sent": (
            "✅ <b>{phone}</b> raqamiga {length} xonali tasdiqlash kodi yuborildi.\n\n"
            "🔢 <b>Yuborilgan kodni kiriting:</b>\n"
            "⏳ Kod {minutes} daqiqa amal qiladi."
        ),
        "sms_failed": "⚠️ SMS yuborishda xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.",
        "resend_wait": "⏳ Kodni qayta yuborish uchun {seconds} soniya kuting.",
        "send_limit": "🚫 SMS yuborish limiti tugadi. Taxminan bir soatdan so'ng qayta urinib ko'ring.",
        "code_format": "❗️ Kod {length} ta raqamdan iborat bo'lishi kerak. Qaytadan kiriting:",
        "code_wrong": "❌ Kod noto'g'ri. Qolgan urinishlar: <b>{left}</b>",
        "code_expired": "⌛️ Kodning amal qilish muddati tugadi. Yangi kod oling.",
        "code_locked": "🚫 Urinishlar soni tugadi. Yangi kod oling.",
        "no_session": "ℹ️ Faol kod topilmadi. Yangi kod oling.",
        "verified": "🎉 Raqamingiz muvaffaqiyatli tasdiqlandi!\n\n📱 <b>{phone}</b>",
        "use_button": "👇 Iltimos, pastdagi <b>«📱 Raqamni yuborish»</b> tugmasini bosing.",
        "enter_code": "🔢 Iltimos, SMS orqali kelgan kodni kiriting.",
        "restart": "Qayta boshlash uchun /start buyrug'ini yuboring.",
    },
    "ru": {
        "start": (
            "Здравствуйте, <b>{name}</b>! 👋\n\n"
            "Чтобы подтвердить номер телефона, нажмите кнопку "
            "<b>«📱 Отправить номер»</b> ниже."
        ),
        "already_verified": (
            "✅ Ваш номер уже подтверждён: <b>{phone}</b>\n\n"
            "Чтобы подтвердить другой номер, нажмите кнопку ниже."
        ),
        "btn_send_phone": "📱 Отправить номер",
        "btn_resend": "🔄 Отправить код повторно",
        "btn_change": "✏️ Изменить номер",
        "phone_placeholder": "Нажмите кнопку",
        "code_placeholder": "Введите код",
        "not_own_contact": "❗️ Пожалуйста, отправьте <b>свой</b> номер с помощью кнопки.",
        "invalid_phone": (
            "❗️ Неверный номер. Отправьте его кнопкой ниже или введите в формате "
            "<code>+998901234567</code>."
        ),
        "phone_accepted": "📨 Номер принят: <b>{phone}</b>",
        "code_sent": (
            "✅ На номер <b>{phone}</b> отправлен {length}-значный код подтверждения.\n\n"
            "🔢 <b>Введите полученный код:</b>\n"
            "⏳ Код действителен {minutes} мин."
        ),
        "sms_failed": "⚠️ Не удалось отправить SMS. Попробуйте ещё раз чуть позже.",
        "resend_wait": "⏳ Повторная отправка будет доступна через {seconds} сек.",
        "send_limit": "🚫 Лимит отправки SMS исчерпан. Попробуйте примерно через час.",
        "code_format": "❗️ Код должен состоять из {length} цифр. Введите ещё раз:",
        "code_wrong": "❌ Неверный код. Осталось попыток: <b>{left}</b>",
        "code_expired": "⌛️ Срок действия кода истёк. Запросите новый код.",
        "code_locked": "🚫 Попытки закончились. Запросите новый код.",
        "no_session": "ℹ️ Активный код не найден. Запросите новый код.",
        "verified": "🎉 Ваш номер успешно подтверждён!\n\n📱 <b>{phone}</b>",
        "use_button": "👇 Пожалуйста, нажмите кнопку <b>«📱 Отправить номер»</b> ниже.",
        "enter_code": "🔢 Пожалуйста, введите код из SMS.",
        "restart": "Чтобы начать заново, отправьте /start.",
    },
}

DEFAULT_LANG = "uz"


def detect_lang(language_code: str | None) -> str:
    if language_code and language_code.lower().startswith("ru"):
        return "ru"
    return DEFAULT_LANG


def t(lang: str, key: str, **kwargs: object) -> str:
    template = TEXTS.get(lang, TEXTS[DEFAULT_LANG]).get(key) or TEXTS[DEFAULT_LANG][key]
    return template.format(**kwargs) if kwargs else template

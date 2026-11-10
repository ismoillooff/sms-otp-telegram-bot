import string

import pytest

from app.texts import DEFAULT_LANG, TEXTS, detect_lang, t


def _placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_all_languages_have_same_keys():
    base = set(TEXTS[DEFAULT_LANG])
    for lang, texts in TEXTS.items():
        assert set(texts) == base, f"{lang} keys differ from {DEFAULT_LANG}"


@pytest.mark.parametrize("key", sorted(TEXTS[DEFAULT_LANG]))
def test_placeholders_match_across_languages(key):
    expected = _placeholders(TEXTS[DEFAULT_LANG][key])
    for lang, texts in TEXTS.items():
        assert _placeholders(texts[key]) == expected, f"{lang}:{key}"


@pytest.mark.parametrize(
    "code, expected",
    [("ru", "ru"), ("ru-RU", "ru"), ("uz", "uz"), ("en", "uz"), (None, "uz")],
)
def test_detect_lang(code, expected):
    assert detect_lang(code) == expected


def test_t_formats_and_falls_back():
    assert "5" in t("ru", "code_wrong", left=5)
    assert t("xx", "btn_send_phone") == TEXTS[DEFAULT_LANG]["btn_send_phone"]

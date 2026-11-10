import pytest

from app.otp import OtpService, ResendCooldown, SendLimitExceeded, VerifyStatus
from app.phone import format_phone, normalize_phone


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make(clock: FakeClock, **kw) -> OtpService:
    params = dict(length=6, ttl=300, max_attempts=3, resend_cooldown=60, max_sends_per_hour=3)
    params.update(kw)
    return OtpService(clock=clock, **params)


def test_correct_code_verifies_once():
    clock = FakeClock()
    otp = make(clock)
    code = otp.issue(1, "998901234567")
    assert len(code) == 6 and code.isdigit()

    result = otp.verify(1, code)
    assert result.status is VerifyStatus.OK
    assert result.phone == "998901234567"
    assert otp.verify(1, code).status is VerifyStatus.NO_SESSION


def test_wrong_code_locks_after_max_attempts():
    clock = FakeClock()
    otp = make(clock)
    code = otp.issue(1, "998901234567")
    wrong = "000000" if code != "000000" else "111111"

    assert otp.verify(1, wrong).attempts_left == 2
    assert otp.verify(1, wrong).attempts_left == 1
    assert otp.verify(1, wrong).status is VerifyStatus.LOCKED
    assert otp.verify(1, code).status is VerifyStatus.NO_SESSION


def test_code_expires():
    clock = FakeClock()
    otp = make(clock)
    code = otp.issue(1, "998901234567")
    clock.now += 301
    assert otp.verify(1, code).status is VerifyStatus.EXPIRED


def test_resend_cooldown_and_hourly_limit():
    clock = FakeClock()
    otp = make(clock)
    otp.issue(1, "998901234567")
    with pytest.raises(ResendCooldown) as exc:
        otp.issue(1, "998901234567")
    assert exc.value.seconds_left == 60

    clock.now += 60
    otp.issue(1, "998901234567")
    clock.now += 60
    otp.issue(1, "998901234567")
    clock.now += 60
    with pytest.raises(SendLimitExceeded):
        otp.issue(1, "998901234567")

    clock.now += 3600
    otp.issue(1, "998901234567")


def test_new_code_invalidates_old_one():
    clock = FakeClock()
    otp = make(clock)
    first = otp.issue(1, "998901234567")
    clock.now += 60
    second = otp.issue(1, "998901234567")
    if first != second:
        assert otp.verify(1, first).status is VerifyStatus.WRONG
    assert otp.verify(1, second).status is VerifyStatus.OK


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("+998 90 123 45 67", "998901234567"),
        ("998901234567", "998901234567"),
        ("901234567", "998901234567"),
        ("+7 999 123 45 67", None),
        ("12345", None),
        ("", None),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


def test_format_phone():
    assert format_phone("998901234567") == "+998 90 123 45 67"

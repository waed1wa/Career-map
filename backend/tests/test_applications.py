"""Заявки: отказ с причиной и сроки. Граничные значения из лекции 9 (TC-06, TC-07)."""

from datetime import datetime, timedelta

import pytest

from app.modules.projects.domain import Application, ApplicationError, ApplicationStatus

START = datetime(2026, 12, 1, 12, 0)


def make() -> Application:
    return Application(student_id="s1", project_id="p1", submitted_at=START)


def test_reject_without_reason_is_forbidden():
    app = make()
    with pytest.raises(ApplicationError):
        app.reject("   ")
    assert app.status == ApplicationStatus.SUBMITTED


def test_reject_with_reason():
    app = make()
    app.reject("Сейчас нужен человек со знанием Docker")
    assert app.status == ApplicationStatus.REJECTED


@pytest.mark.parametrize(
    ("passed", "expected"),
    [
        (timedelta(days=4, hours=23), False),  # чуть меньше границы
        (timedelta(days=5), True),  # ровно граница
        (timedelta(days=6), True),
    ],
)
def test_reminder_on_day_5(passed, expected):
    assert make().needs_reminder(START + passed) is expected


def test_reminder_is_sent_once():
    app = make()
    app.reminder_sent = True
    assert app.needs_reminder(START + timedelta(days=6)) is False


@pytest.mark.parametrize(
    ("passed", "expired"),
    [
        (timedelta(days=6, hours=23, minutes=59), False),
        (timedelta(days=7), True),
    ],
)
def test_expired_on_day_7(passed, expired):
    app = make()
    assert app.expire_if_overdue(START + passed) is expired
    assert (app.status == ApplicationStatus.EXPIRED) is expired


def test_answered_application_never_expires():
    app = make()
    app.accept()
    assert app.expire_if_overdue(START + timedelta(days=30)) is False
    assert app.status == ApplicationStatus.ACCEPTED


def test_cannot_answer_twice():
    app = make()
    app.accept()
    with pytest.raises(ApplicationError):
        app.reject("Передумали, извините за путаницу")

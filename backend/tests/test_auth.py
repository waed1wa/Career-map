"""Модуль «Вход и роли»: классы эквивалентности и граничные значения (лекция 9)."""

import pytest

from app.modules.auth.domain import AuthError, EmailTakenError, Role, check_password, normalize_email
from app.modules.auth.ports import InMemoryUserRepository
from app.modules.auth.security import PasswordHasher, TokenError, TokenService
from app.modules.auth.service import WRONG_CREDENTIALS, AuthService

SECRET = "test-secret-test-secret-test-secret"


@pytest.fixture
def service() -> AuthService:
    # 1000 итераций вместо 600 000 — только чтобы тесты шли быстро
    return AuthService(InMemoryUserRepository(), PasswordHasher(iterations=1_000), TokenService(SECRET, 3600))


# --- Почта -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("student@mail.ru", "student@mail.ru"), ("  Student@Mail.RU ", "student@mail.ru")],
    ids=["valid", "spaces-and-case"],
)
def test_email_is_normalized(raw, expected):
    assert normalize_email(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "student", "student@", "@mail.ru", "student@mail", "stu dent@mail.ru", "a" * 250 + "@x.ru"],
    ids=["empty", "no-at", "no-domain", "no-name", "no-dot", "space-inside", "too-long"],
)
def test_bad_email_is_rejected(raw):
    with pytest.raises(AuthError):
        normalize_email(raw)


# --- Пароль: границы 8 и 64 символа ------------------------------------------------------


@pytest.mark.parametrize(
    "password",
    ["abc1234", "a1" * 32 + "x"],
    ids=["7-chars", "65-chars"],
)
def test_password_length_out_of_bounds(password):
    with pytest.raises(AuthError, match="от 8 до 64"):
        check_password(password)


@pytest.mark.parametrize("password", ["abcd1234", "a1" * 32], ids=["8-chars", "64-chars"])
def test_password_length_on_bounds(password):
    check_password(password)  # не бросает ошибку


@pytest.mark.parametrize("password", ["abcdefgh", "12345678"], ids=["no-digit", "no-letter"])
def test_password_needs_letter_and_digit(password):
    with pytest.raises(AuthError, match="букв"):
        check_password(password)


# --- Регистрация ----------------------------------------------------------------------


def test_register_student(service):
    user = service.register("Student@Mail.ru", "secret123", "student", consent=True)

    assert user.email == "student@mail.ru"
    assert user.role == Role.STUDENT
    assert user.consent_at is not None


def test_register_organizer(service):
    assert service.register("org@mail.ru", "secret123", "organizer", consent=True).role == Role.ORGANIZER


def test_register_without_consent_is_forbidden(service):
    """152-ФЗ: без согласия на обработку персональных данных не регистрируем."""
    with pytest.raises(AuthError, match="согласия"):
        service.register("student@mail.ru", "secret123", "student", consent=False)


def test_admin_role_cannot_be_registered(service):
    with pytest.raises(AuthError, match="Роль"):
        service.register("hacker@mail.ru", "secret123", "admin", consent=True)


def test_same_email_twice_is_rejected_case_insensitive(service):
    service.register("student@mail.ru", "secret123", "student", consent=True)

    with pytest.raises(EmailTakenError):
        service.register("STUDENT@mail.ru", "other1234", "student", consent=True)


def test_password_is_not_stored_in_plain_text(service):
    user = service.register("student@mail.ru", "secret123", "student", consent=True)

    assert "secret123" not in user.password_hash
    assert user.password_hash.startswith("pbkdf2_sha256$")


def test_same_password_gives_different_hashes():
    """Соль: у двух людей с одинаковым паролем хеши разные."""
    hasher = PasswordHasher(iterations=1_000)
    assert hasher.hash("secret123") != hasher.hash("secret123")


# --- Вход и токен ------------------------------------------------------------------------


def test_login_and_who_am_i(service):
    user = service.register("student@mail.ru", "secret123", "student", consent=True)

    token = service.login(" Student@mail.ru", "secret123")

    assert service.current_user(token).id == user.id


@pytest.mark.parametrize(
    ("email", "password"),
    [("student@mail.ru", "wrong1234"), ("nobody@mail.ru", "secret123"), ("not-an-email", "secret123")],
    ids=["wrong-password", "unknown-email", "bad-email"],
)
def test_login_fails_with_the_same_message(service, email, password):
    """Одинаковый ответ: по нему нельзя узнать, зарегистрирована ли почта."""
    service.register("student@mail.ru", "secret123", "student", consent=True)

    with pytest.raises(AuthError) as error:
        service.login(email, password)
    assert str(error.value) == WRONG_CREDENTIALS


def test_tampered_token_is_rejected(service):
    service.register("student@mail.ru", "secret123", "student", consent=True)
    token = service.login("student@mail.ru", "secret123")
    body, signature = token.split(".")
    fake_body = body[:-2] + ("AA" if body[-2:] != "AA" else "BB")

    with pytest.raises(AuthError):
        service.current_user(f"{fake_body}.{signature}")


def test_token_expires():
    now = [1_000_000.0]
    tokens = TokenService(SECRET, ttl_seconds=60, clock=lambda: now[0])
    token = tokens.issue("user-1", "student")

    now[0] += 60  # ровно на границе — ещё действует
    assert tokens.read(token)["sub"] == "user-1"
    now[0] += 1  # секундой позже — уже нет
    with pytest.raises(TokenError):
        tokens.read(token)


def test_short_secret_is_not_allowed():
    with pytest.raises(ValueError):
        TokenService("short", 3600)

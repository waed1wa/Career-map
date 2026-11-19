"""Хеширование паролей и токены входа. Только стандартная библиотека Python.

Пароль храним как PBKDF2-SHA256 с солью: даже если базу украдут, пароли не прочитать.
Токен — подписанная HMAC-SHA256 строка «данные.подпись» со сроком действия.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Callable
from functools import lru_cache
from typing import Any

# Рекомендация OWASP для PBKDF2-SHA256. В тестах передаём меньше, чтобы они шли быстро.
DEFAULT_ITERATIONS = 600_000
_ALGO = "pbkdf2_sha256"


class PasswordHasher:
    def __init__(self, iterations: int = DEFAULT_ITERATIONS):
        self.iterations = iterations

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, self.iterations)
        return f"{_ALGO}${self.iterations}${salt.hex()}${digest.hex()}"

    def verify(self, password: str, stored: str) -> bool:
        try:
            algo, iterations, salt_hex, digest_hex = stored.split("$")
            salt = bytes.fromhex(salt_hex)
            rounds = int(iterations)
        except ValueError:
            return False
        if algo != _ALGO:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, rounds)
        return hmac.compare_digest(digest.hex(), digest_hex)  # сравнение без утечки по времени

    def dummy_hash(self) -> str:
        """Хеш-пустышка: проверяем пароль и для несуществующей почты, чтобы по времени ответа
        нельзя было понять, зарегистрирован ли человек."""
        return _dummy_hash(self.iterations)


@lru_cache
def _dummy_hash(iterations: int) -> str:
    return PasswordHasher(iterations).hash("dummy-password-1")


class TokenError(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class TokenService:
    def __init__(self, secret: str, ttl_seconds: int, clock: Callable[[], float] = time.time):
        if len(secret) < 32:
            raise ValueError("SECRET_KEY должен быть не короче 32 символов")
        self._secret = secret.encode()
        self._ttl = ttl_seconds
        self._clock = clock

    def issue(self, user_id: str, role: str) -> str:
        payload = {"sub": user_id, "role": role, "exp": int(self._clock()) + self._ttl}
        body = _b64(json.dumps(payload, separators=(",", ":")).encode())
        return f"{body}.{self._sign(body)}"

    def read(self, token: str) -> dict[str, Any]:
        try:
            body, signature = token.split(".")
        except ValueError:
            raise TokenError("Неверный токен") from None
        if not hmac.compare_digest(signature, self._sign(body)):
            raise TokenError("Подпись не совпадает")
        payload: dict[str, Any] = json.loads(_unb64(body))
        if payload["exp"] < self._clock():
            raise TokenError("Срок действия токена истёк")
        return payload

    def _sign(self, body: str) -> str:
        return _b64(hmac.new(self._secret, body.encode(), hashlib.sha256).digest())

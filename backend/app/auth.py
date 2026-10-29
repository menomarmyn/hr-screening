"""Пользователи и права: хеш паролей (PBKDF2), JWT, зависимости FastAPI для ролей.

Роли:
  candidate — видит публичные вакансии, подаёт отклики, видит только свои отклики и их этап;
  hr        — управляет вакансиями и профилем компании, видит все отклики, резюме и оценки ИИ.
Сервисный X-API-Key (скрипты, MCP-сервер) работает с правами HR.
"""

import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

PBKDF2_ITER = 240_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITER)
    return f"pbkdf2_sha256${PBKDF2_ITER}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iters))
    return hmac.compare_digest(check.hex(), digest)


def create_token(user: User) -> str:
    s = get_settings()
    payload = {"sub": str(user.id), "role": user.role, "exp": datetime.now(UTC) + timedelta(hours=s.jwt_ttl_hours)}
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


@dataclass
class Principal:
    id: int | None  # None — сервисный ключ
    role: str
    email: str = ""
    full_name: str = ""

    @property
    def is_hr(self) -> bool:
        return self.role == "hr"


def _from_token(token: str, db: Session) -> Principal:
    try:
        data = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(401, "Сессия истекла, войдите снова") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(401, "Недействительный токен") from e
    user = db.get(User, int(data["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(401, "Пользователь не найден")
    return Principal(user.id, user.role, user.email, user.full_name)


def optional_user(
    authorization: str = Header(default=""), x_api_key: str = Header(default=""), db: Session = Depends(get_db)
) -> Principal | None:
    if x_api_key:
        if not hmac.compare_digest(x_api_key, get_settings().api_key):
            raise HTTPException(401, "Неверный X-API-Key")
        return Principal(None, "hr", "service")
    if authorization.lower().startswith("bearer "):
        return _from_token(authorization[7:], db)
    return None


def current_user(p: Principal | None = Depends(optional_user)) -> Principal:
    if p is None:
        raise HTTPException(401, "Нужно войти в аккаунт")
    return p


def require_hr(p: Principal = Depends(current_user)) -> Principal:
    if not p.is_hr:
        raise HTTPException(403, "Доступно только HR")
    return p


def require_candidate(p: Principal = Depends(current_user)) -> Principal:
    if p.role != "candidate":
        raise HTTPException(403, "Откликаться могут только кандидаты")
    return p

"""OAuth provider 토큰 암·복호화 (Fernet / OAUTH_TOKEN_KEY)."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet | None:
    key = (settings.OAUTH_TOKEN_KEY or "").strip()
    if not key:
        return None
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError):
        return None


def encrypt_token(plaintext: str | None) -> bytes | None:
    if not plaintext:
        return None
    f = _fernet()
    if f is None:
        return None
    return f.encrypt(plaintext.encode("utf-8"))


def decrypt_token(ciphertext: bytes | None) -> str | None:
    if not ciphertext:
        return None
    f = _fernet()
    if f is None:
        return None
    try:
        return f.decrypt(ciphertext).decode("utf-8")
    except InvalidToken:
        return None

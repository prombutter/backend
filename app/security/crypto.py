"""OAuth provider 토큰 암·복호화 (Fernet / OAUTH_TOKEN_KEY)."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet() -> Fernet | None:
    key = (settings.oauth_token_key or "").strip()
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
        # 키 미설정 시 원문 저장 금지 — 토큰 보관 생략
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

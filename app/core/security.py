"""
인증 코어 (security primitives) — PB-67

- 비밀번호: bcrypt 해싱/검증 (rounds = settings.BCRYPT_ROUNDS)
- JWT: access(15분) · refresh(3시간) 발급/검증
- 해시 헬퍼: refresh token DB 저장용(user_sessions.refresh_token_hash) / login_attempts.email_hash용

엔드포인트(signup·login·refresh·logout·me)에서 갖다 쓰는 부품.
FastAPI·DB에 의존하지 않는 순수 함수 모음.
위치: app/core/security.py
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.core.config import settings

# ===== 비밀번호 (bcrypt) =====
# 주의: passlib는 최신 bcrypt(4.x)와 호환이 깨져 있어(백엔드 초기화 시 에러) bcrypt를 직접 쓴다.
# (bcrypt는 passlib[bcrypt] 설치에 이미 포함됨.) 추후 pyproject에서 passlib은 제거 가능.
# bcrypt는 입력을 72바이트까지만 사용하고 4.x는 초과 시 에러를 내므로, 명시적으로 자른다.
_BCRYPT_MAX_BYTES = 72


def hash_password(plain_password: str) -> str:
    """평문 비밀번호 → bcrypt 해시 (DB의 users.password_hash에 저장)."""
    pwd = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pwd, bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """로그인 시 평문 ↔ 저장된 해시 비교."""
    pwd = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(pwd, password_hash.encode("utf-8"))


# ===== JWT =====
ACCESS = "access"
REFRESH = "refresh"


def _create_token(subject: str, token_type: str, expires_minutes: int, **extra) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),          # 보통 user.id
        "type": token_type,           # access / refresh 구분
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
        **extra,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str) -> str:
    return _create_token(subject, ACCESS, settings.ACCESS_TOKEN_EXPIRE_MINUTES)


def create_refresh_token(subject: str) -> tuple[str, str]:
    """리프레시 토큰과 그 jti를 반환. jti(고유 id)로 세션 추적·회전(rotation)에 사용."""
    jti = str(uuid.uuid4())
    token = _create_token(subject, REFRESH, settings.REFRESH_TOKEN_EXPIRE_MINUTES, jti=jti)
    return token, jti


def decode_token(token: str) -> dict:
    """서명·만료 검증 후 claims(dict) 반환. 유효하지 않으면 jose.JWTError 발생."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# ===== 해시 헬퍼 (단방향 SHA-256, DB 저장/조회용) =====
def hash_token(token: str) -> str:
    """refresh token을 평문으로 저장하지 않고 SHA-256 해시로 user_sessions에 저장."""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_email(email: str) -> str:
    """login_attempts.email_hash — 소문자/trim 정규화 후 SHA-256 (원본 이메일 미저장)."""
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()
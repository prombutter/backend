"""
SQLAlchemy ORM 모델 — PB-67 (인증 + 워크스페이스)

prombutter.sql 스키마를 그대로 미러링한다 (DB-first).
테이블/enum 타입은 이미 DB에 존재하므로(=bootstrap), 모델은 "매핑"만 담당하고
DDL은 생성하지 않는다(create_type=False). 마이그레이션 소유는 안승준(Q5).

위치: app/models.py
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import BYTEA, CITEXT, ENUM, INET, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """모든 모델의 베이스. db.py의 async 엔진과 함께 쓴다."""


# ===== Enum (DB의 PG enum 타입과 1:1) =====
class UserRole(str, enum.Enum):
    USER = "USER"
    SUPER_ADMIN = "SUPER_ADMIN"


class AuthProvider(str, enum.Enum):
    EMAIL = "EMAIL"
    GOOGLE = "GOOGLE"


class TokenType(str, enum.Enum):
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    PASSWORD_RESET = "PASSWORD_RESET"


# ENUM 컬럼 공통 옵션: 타입은 DB에 이미 있으므로 새로 만들지 않음
_user_role = ENUM(UserRole, name="user_role", create_type=False)
_auth_provider = ENUM(AuthProvider, name="auth_provider", create_type=False)
_token_type = ENUM(TokenType, name="token_type", create_type=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)  # 대소문자 무시
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))  # 이메일 가입자만 (Google=NULL)
    role: Mapped[UserRole] = mapped_column(
        _user_role, server_default=text("'USER'"), nullable=False
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    last_failed_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    extension_first_detected_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    extension_last_detected_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    # owner_id UNIQUE = 사용자당 워크스페이스 1:1
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(100), server_default=text("'내 워크스페이스'"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uk_user_identities_provider"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    provider: Mapped[AuthProvider] = mapped_column(_auth_provider, nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[bytes | None] = mapped_column(BYTEA)  # 암호화 저장 전제
    refresh_token: Mapped[bytes | None] = mapped_column(BYTEA)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    device_info: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))  # logout 시 set
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))  # NULL=미사용
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    token_type: Mapped[TokenType] = mapped_column(_token_type, nullable=False)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ip_address: Mapped[str | None] = mapped_column(INET)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # 소문자/trim 후 SHA-256

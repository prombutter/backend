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


from .base import Base


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


# ===== PB-72: 프롬프트 계열 (프롬프트 / 블록 / 변수) =====
class BlockType(str, enum.Enum):
    PART = "PART"
    INLINE = "INLINE"


class VariableEntityType(str, enum.Enum):
    PROMPT = "PROMPT"
    PART = "PART"


_block_type = ENUM(BlockType, name="block_type", create_type=False)
_variable_entity_type = ENUM(
    VariableEntityType, name="variable_entity_type", create_type=False
)


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)  # 워크스페이스 내 중복 불가
    favorited_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )  # 즐겨찾기(♥) 등록 시각 — NULL=미등록. 워크스페이스당 5개 상한(PB-72)
    deleted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))  # Soft Delete
    purge_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True)
    )  # 영구 삭제 예정(deleted_at + 30일)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class PromptBlock(Base):
    __tablename__ = "prompt_blocks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompts.id"), nullable=False
    )
    # part_id: block_type=PART 일 때만. DB엔 fk_prompt_blocks_part(→parts.id)가 있으나
    # parts 모델은 PB-92 소관이라 ORM엔 매핑하지 않는다(있으면 flush 시 FK 해석 실패).
    # 참조 존재/소유 검증은 라우터의 _validate_part_refs가 담당.
    part_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    inline_body: Mapped[str | None] = mapped_column(String(700))  # block_type=INLINE 일 때 (700자)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    block_type: Mapped[BlockType] = mapped_column(_block_type, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )


class Variable(Base):
    __tablename__ = "variables"

    # 복합 PK: (entity_type, entity_id, name) — 엔티티(프롬프트/파츠)별 변수명 유일
    entity_type: Mapped[VariableEntityType] = mapped_column(
        _variable_entity_type, primary_key=True
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    has_conflict: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )  # 변수명 충돌 여부

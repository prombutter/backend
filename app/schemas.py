"""
Pydantic 입출력 스키마 — PB-67 (인증 + 워크스페이스)

models.py(DB 테이블)와 구분: 이건 API 요청/응답의 "모양".
응답 스키마는 password_hash 같은 민감 컬럼을 노출하지 않는다.

위치: app/schemas.py
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import UserRole


# ===== 요청 (Request) =====
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt 72바이트 상한
    name: str | None = Field(default=None, max_length=100)  # 없으면 email local-part로 채움


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


# ===== 응답 (Response) =====
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ORM 객체 → 스키마 변환 허용

    id: uuid.UUID
    email: EmailStr
    name: str
    role: UserRole
    created_at: datetime


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime


# ===== PB-72: 프롬프트 요청/응답 =====
class PromptCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)  # 워크스페이스 내 중복 불가(라우터에서 검사)


class PromptUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)


class PromptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    favorited_at: datetime | None  # NULL=미등록 — FE는 null 여부로 ♥ 표시
    created_at: datetime
    updated_at: datetime

"""
Pydantic 입출력 스키마 — PB-67 (인증 + 워크스페이스)

models.py(DB 테이블)와 구분: 이건 API 요청/응답의 "모양".
응답 스키마는 password_hash 같은 민감 컬럼을 노출하지 않는다.

위치: app/schemas.py
"""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import UserRole

# 비밀번호 정책 (인증 명세 1.5): 8자 이상 + 영문·숫자·특수문자 각 1개 이상
_PW_SPECIAL = r"""!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?~`"""


# ===== 요청 (Request) =====
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt 72바이트 상한
    name: str | None = Field(default=None, max_length=100)  # 없으면 email local-part로 채움

    @field_validator("password")
    @classmethod
    def _password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("비밀번호에 영문을 1자 이상 포함해야 합니다")
        if not re.search(r"[0-9]", v):
            raise ValueError("비밀번호에 숫자를 1자 이상 포함해야 합니다")
        if not re.search(f"[{re.escape(_PW_SPECIAL)}]", v):
            raise ValueError("비밀번호에 특수문자를 1자 이상 포함해야 합니다")
        return v


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

"""
Pydantic 입출력 스키마 — PB-67 (인증 + 워크스페이스)

models.py(DB 테이블)와 구분: 이건 API 요청/응답의 "모양".
응답 스키마는 password_hash 같은 민감 컬럼을 노출하지 않는다.

위치: app/schemas.py
"""

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import BlockType, UserRole

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


# ===== PB-72: 프롬프트 요청/응답 =====
# 블록 개수(10)·인라인 길이(700) 상한은 라우터에서 검사한다 — 정본 전용 에러코드
# (ERR-BLOCK-001 / ERR-BODY-002)를 내보내기 위해 pydantic max_length 대신 명시 검증.


class BlockInput(BaseModel):
    """프롬프트에 담기는 블록 1개. 순서는 배열 위치로 정해진다(sort_order 별도 입력 없음).

    - INLINE: inline_body 필수(길이 검사는 라우터), part_id 금지
    - PART:   part_id 필수(파츠 참조), inline_body 금지 — 존재/소유는 라우터에서 검증
    """

    block_type: BlockType
    inline_body: str | None = None
    part_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _check_shape(self) -> "BlockInput":
        if self.block_type == BlockType.INLINE:
            if not (self.inline_body and self.inline_body.strip()):
                raise ValueError("INLINE 블록은 inline_body가 필요해요.")
            if self.part_id is not None:
                raise ValueError("INLINE 블록에는 part_id를 넣을 수 없어요.")
        else:  # PART
            if self.part_id is None:
                raise ValueError("PART 블록은 part_id가 필요해요.")
            if self.inline_body is not None:
                raise ValueError("PART 블록에는 inline_body를 넣을 수 없어요.")
        return self


class PromptCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)  # 워크스페이스 내 중복 불가(라우터에서 검사)
    blocks: list[BlockInput] = Field(default_factory=list)


class PromptUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    # blocks 생략(None) → 기존 유지 / [] → 전부 삭제 / [..] → 통째로 교체
    blocks: list[BlockInput] | None = None


class BlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    block_type: BlockType
    inline_body: str | None
    part_id: uuid.UUID | None
    sort_order: int


class PromptResponse(BaseModel):
    """목록용(가벼움) — 블록 미포함."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    favorited_at: datetime | None  # NULL=미등록 — FE는 null 여부로 ♥ 표시
    created_at: datetime
    updated_at: datetime


class PromptDetailResponse(PromptResponse):
    """단건/생성/수정용 — 블록 포함(sort_order 오름차순)."""

    blocks: list[BlockResponse]


class RenderRequest(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)  # {변수명: 값}. 없는 값은 미치환


class RenderResponse(BaseModel):
    rendered: str
    missing: list[str]  # 값이 안 들어와 {{...}} 자리표시자로 남은 변수(첫 등장 순)


class VariablesResponse(BaseModel):
    variables: list[str]  # 프롬프트 블록에서 뽑은 변수명(첫 등장 순, 중복 제거)

from pydantic import EmailStr, Field

class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="이메일 주소")

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="재설정 토큰")
    new_password: str = Field(..., min_length=8, max_length=72, description="새 비밀번호")

    @field_validator("new_password")
    @classmethod
    def _password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("비밀번호에 영문을 1자 이상 포함해야 합니다")
        if not re.search(r"[0-9]", v):
            raise ValueError("비밀번호에 숫자를 1자 이상 포함해야 합니다")
        if not re.search(f"[{re.escape(_PW_SPECIAL)}]", v):
            raise ValueError("비밀번호에 특수문자를 1자 이상 포함해야 합니다")
        return v

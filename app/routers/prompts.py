"""
프롬프트 라우터 — PB-72 (Phase 2: title-level CRUD)

POST   /prompts        생성
GET    /prompts        목록(soft-delete 제외)
GET    /prompts/{id}   단건 조회
PATCH  /prompts/{id}   제목 수정
DELETE /prompts/{id}   소프트 삭제(deleted_at, purge_at=+30일)

스코프: 모든 엔드포인트는 현재 유저의 워크스페이스로 한정.
정책(PB-72): title은 워크스페이스 내 중복 불가(라우터에서 검사, 409).
             DB에 (workspace_id, title) UNIQUE 제약이 없어 앱 계층에서 검사한다.
             블록·변수·즐겨찾기는 다음 Phase.

위치: app/routers/prompts.py
"""

import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import column, delete, func, select, table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import get_session
from app.deps import get_current_workspace
from app.models import BlockType, Prompt, PromptBlock, Workspace
from app.schemas import (
    BlockInput,
    BlockResponse,
    PromptCreate,
    PromptDetailResponse,
    PromptResponse,
    PromptUpdate,
    RenderRequest,
    RenderResponse,
    VariablesResponse,
)

# {{ 이름 }} — 양옆 공백 허용, 이름엔 중괄호/개행 불가. group(1)=변수명(공백 trim은 아래서)
_VAR_RE = re.compile(r"\{\{\s*([^{}\n]+?)\s*\}\}")

router = APIRouter(prefix="/prompts", tags=["prompts"])

PURGE_AFTER_DAYS = 30  # 소프트 삭제 후 영구 삭제까지 유예
FAVORITE_LIMIT = 5  # 워크스페이스당 즐겨찾기(★) 상한 (PB-72 확정 정책, 초과=ERR-FAV-002/422)
MAX_BLOCKS = 10  # 프롬프트당 블록 상한 (STRUCT-001 §5, 초과=ERR-BLOCK-001/422)
INLINE_MAX_CHARS = 700  # 인라인 텍스트 상한 (STRUCT-001 §5.2, 초과=ERR-BODY-002/422)

# parts 테이블은 PB-89 소관이라 ORM 모델을 두지 않는다(향후 Part 모델과 충돌 방지).
# PART 블록 참조 검증용으로 필요한 컬럼만 Core table로 가볍게 매핑(읽기 전용).
_parts = table(
    "parts",
    column("id", PG_UUID(as_uuid=True)),
    column("workspace_id", PG_UUID(as_uuid=True)),
    column("deleted_at"),
)


async def _title_taken(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    title: str,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    """같은 워크스페이스에 (삭제 안 된) 동일 제목 프롬프트가 있는지. 수정 시 자기 자신은 제외."""
    stmt = select(Prompt.id).where(
        Prompt.workspace_id == workspace_id,
        Prompt.title == title,
        Prompt.deleted_at.is_(None),
    )
    if exclude_id is not None:
        stmt = stmt.where(Prompt.id != exclude_id)
    return await session.scalar(stmt) is not None


async def _active_favorite_count(session: AsyncSession, workspace_id: uuid.UUID) -> int:
    """워크스페이스의 현재 즐겨찾기 개수 (삭제 안 된 것만)."""
    return await session.scalar(
        select(func.count())
        .select_from(Prompt)
        .where(
            Prompt.workspace_id == workspace_id,
            Prompt.favorited_at.is_not(None),
            Prompt.deleted_at.is_(None),
        )
    )


async def _get_active_prompt(
    session: AsyncSession, workspace: Workspace, prompt_id: uuid.UUID
) -> Prompt:
    """워크스페이스에 속한 (삭제 안 된) 프롬프트를 찾거나 404.

    다른 워크스페이스의 프롬프트는 '없음'과 동일하게 취급(존재 노출 방지).
    """
    prompt = await session.get(Prompt, prompt_id)
    if prompt is None or prompt.workspace_id != workspace.id or prompt.deleted_at is not None:
        raise AppError(
            status.HTTP_404_NOT_FOUND, "ERR-PROMPT-NOT-FOUND", "프롬프트를 찾을 수 없어요."
        )
    return prompt


async def _validate_part_refs(
    session: AsyncSession, workspace_id: uuid.UUID, blocks: list[BlockInput]
) -> None:
    """PART 블록이 참조하는 파츠가 내 워크스페이스에 살아있는지 확인. 없으면 422.

    파츠 생성 경로(PB-89)가 아직 없어 현 단계에선 PART 블록이 사실상 막힌다(정상).
    """
    part_ids = [b.part_id for b in blocks if b.block_type == BlockType.PART]
    if not part_ids:
        return
    valid = set(
        await session.scalars(
            select(_parts.c.id).where(
                _parts.c.id.in_(part_ids),
                _parts.c.workspace_id == workspace_id,
                _parts.c.deleted_at.is_(None),
            )
        )
    )
    missing = [pid for pid in part_ids if pid not in valid]
    if missing:
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "ERR-BLOCK-INVALID-PART",
            f"참조한 파츠를 찾을 수 없어요: {missing[0]}",
        )


def _validate_blocks(blocks: list[BlockInput]) -> None:
    """블록 개수·인라인 길이 상한 검사 — 정본 전용 에러코드 사용.

    (shape 검증은 스키마 BlockInput._check_shape가, 개수/길이는 여기서.)
    """
    if len(blocks) > MAX_BLOCKS:
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "ERR-BLOCK-001",
            f"블록은 최대 {MAX_BLOCKS}개까지 추가할 수 있어요.",
        )
    for b in blocks:
        if (
            b.block_type == BlockType.INLINE
            and b.inline_body
            and len(b.inline_body) > INLINE_MAX_CHARS
        ):
            raise AppError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "ERR-BODY-002",
                f"텍스트는 {INLINE_MAX_CHARS}자까지 쓸 수 있어요.",
            )


def _build_blocks(prompt_id: uuid.UUID, blocks: list[BlockInput]) -> list[PromptBlock]:
    """입력 블록을 PromptBlock ORM으로. 배열 위치가 곧 sort_order(0부터)."""
    return [
        PromptBlock(
            prompt_id=prompt_id,
            block_type=b.block_type,
            inline_body=b.inline_body,
            part_id=b.part_id,
            sort_order=i,
        )
        for i, b in enumerate(blocks)
    ]


async def _load_blocks(session: AsyncSession, prompt_id: uuid.UUID) -> list[PromptBlock]:
    """프롬프트의 블록을 sort_order 오름차순으로 로드."""
    return list(
        await session.scalars(
            select(PromptBlock)
            .where(PromptBlock.prompt_id == prompt_id)
            .order_by(PromptBlock.sort_order)
        )
    )


async def _detail(session: AsyncSession, prompt: Prompt) -> PromptDetailResponse:
    """프롬프트 + 블록(sort_order 순)을 상세 응답으로 조립."""
    blocks = await _load_blocks(session, prompt.id)
    return PromptDetailResponse(
        id=prompt.id,
        workspace_id=prompt.workspace_id,
        title=prompt.title,
        favorited_at=prompt.favorited_at,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        blocks=[BlockResponse.model_validate(b) for b in blocks],
    )


def _assemble_text(blocks: list[PromptBlock]) -> str:
    """블록을 순서대로 이어붙인 원본 텍스트(줄바꿈 구분).

    INLINE = inline_body. PART = 파츠 본문 병합이 필요하나 파츠 생성 경로(PB-89)가
    없어 현재 저장 가능한 프롬프트엔 PART 블록이 없다. 방어적으로 빈 조각 처리.
    """
    pieces: list[str] = []
    for b in blocks:
        if b.block_type == BlockType.INLINE:
            pieces.append(b.inline_body or "")
        else:  # PART — TODO(PB-89): 참조 파츠 본문 삽입 + 변수 병합/충돌(has_conflict)
            pieces.append("")
    return "\n".join(pieces)


def _extract_var_names(text: str) -> list[str]:
    """텍스트에서 {{변수}} 이름을 첫 등장 순·중복 제거로 추출."""
    names = (m.strip() for m in _VAR_RE.findall(text))
    return list(dict.fromkeys(n for n in names if n))


def _render_text(text: str, values: dict[str, str]) -> tuple[str, list[str]]:
    """{{name}}을 values로 치환. 값 없는 변수는 자리표시자로 남기고 missing에 모은다."""
    missing: list[str] = []
    seen: set[str] = set()

    def repl(m: re.Match) -> str:
        name = m.group(1).strip()
        if name in values:
            return str(values[name])
        if name not in seen:
            seen.add(name)
            missing.append(name)
        return m.group(0)  # 값 없음 → {{...}} 그대로

    return _VAR_RE.sub(repl, text), missing


@router.post("", response_model=PromptDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    body: PromptCreate,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session),
) -> PromptDetailResponse:
    if await _title_taken(session, workspace.id, body.title):
        raise AppError(
            status.HTTP_409_CONFLICT,
            "ERR-TITLE-001",
            "같은 이름의 프롬프트가 이미 있어요. 다른 이름을 써 주세요.",
        )
    _validate_blocks(body.blocks)
    await _validate_part_refs(session, workspace.id, body.blocks)
    prompt = Prompt(workspace_id=workspace.id, title=body.title)
    session.add(prompt)
    await session.flush()  # prompt.id 확보 (블록 FK)
    session.add_all(_build_blocks(prompt.id, body.blocks))
    await session.commit()
    await session.refresh(prompt)
    return await _detail(session, prompt)


@router.get("", response_model=list[PromptResponse])
async def list_prompts(
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session),
) -> list[Prompt]:
    stmt = (
        select(Prompt)
        .where(Prompt.workspace_id == workspace.id, Prompt.deleted_at.is_(None))
        .order_by(Prompt.created_at.desc())
    )
    return list(await session.scalars(stmt))


@router.get("/{prompt_id}", response_model=PromptDetailResponse)
async def get_prompt(
    prompt_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session),
) -> PromptDetailResponse:
    prompt = await _get_active_prompt(session, workspace, prompt_id)
    return await _detail(session, prompt)


@router.patch("/{prompt_id}", response_model=PromptDetailResponse)
async def update_prompt(
    prompt_id: uuid.UUID,
    body: PromptUpdate,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session),
) -> PromptDetailResponse:
    prompt = await _get_active_prompt(session, workspace, prompt_id)
    changed = False

    if body.title is not None and body.title != prompt.title:
        if await _title_taken(session, workspace.id, body.title, exclude_id=prompt.id):
            raise AppError(
                status.HTTP_409_CONFLICT,
                "ERR-TITLE-001",
                "같은 이름의 프롬프트가 이미 있어요. 다른 이름을 써 주세요.",
            )
        prompt.title = body.title
        changed = True

    if body.blocks is not None:  # 통째로 교체(생략이면 유지). []면 전부 삭제
        _validate_blocks(body.blocks)
        await _validate_part_refs(session, workspace.id, body.blocks)
        await session.execute(delete(PromptBlock).where(PromptBlock.prompt_id == prompt.id))
        session.add_all(_build_blocks(prompt.id, body.blocks))
        changed = True

    if changed:
        prompt.updated_at = datetime.now(timezone.utc)  # DB에 자동 갱신 트리거 없음 → 명시적
    await session.commit()
    await session.refresh(prompt)
    return await _detail(session, prompt)


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session),
) -> None:
    prompt = await _get_active_prompt(session, workspace, prompt_id)  # 이미 삭제됨 → 404
    now = datetime.now(timezone.utc)
    prompt.deleted_at = now
    prompt.purge_at = now + timedelta(days=PURGE_AFTER_DAYS)
    await session.commit()


@router.post("/{prompt_id}/favorite", response_model=PromptResponse)
async def add_favorite(
    prompt_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session),
) -> Prompt:
    """즐겨찾기(★) 등록. 이미 ★면 멱등(현재 상태 반환).
    새로 등록 시 워크스페이스 상한(5개) 초과면 422로 차단(자동삭제 X)."""
    prompt = await _get_active_prompt(session, workspace, prompt_id)
    if prompt.favorited_at is not None:  # 이미 등록됨 → 멱등, 상한 검사 불필요
        return prompt
    if await _active_favorite_count(session, workspace.id) >= FAVORITE_LIMIT:
        # 쿼터/상한 초과 = 422로 통일 (BE 확정, ERR-001 정본코드·문구 ERR-FAV-002)
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "ERR-FAV-002",
            f"프롬프트 즐겨찾기는 {FAVORITE_LIMIT}개까지 등록할 수 있어요. 일부를 해제한 뒤 다시 시도해 주세요.",
        )
    prompt.favorited_at = datetime.now(timezone.utc)  # updated_at은 건드리지 않음(수정 순서 보존)
    await session.commit()
    await session.refresh(prompt)
    return prompt


@router.delete("/{prompt_id}/favorite", response_model=PromptResponse)
async def remove_favorite(
    prompt_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session),
) -> Prompt:
    """즐겨찾기(★) 해제. 이미 해제 상태여도 멱등(현재 상태 반환)."""
    prompt = await _get_active_prompt(session, workspace, prompt_id)
    if prompt.favorited_at is not None:
        prompt.favorited_at = None
        await session.commit()
        await session.refresh(prompt)
    return prompt


@router.get("/{prompt_id}/variables", response_model=VariablesResponse)
async def get_prompt_variables(
    prompt_id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session),
) -> VariablesResponse:
    """프롬프트 블록에서 뽑은 변수명 목록(첫 등장 순). 익스텐션 변수 입력 폼용."""
    prompt = await _get_active_prompt(session, workspace, prompt_id)
    blocks = await _load_blocks(session, prompt.id)
    return VariablesResponse(variables=_extract_var_names(_assemble_text(blocks)))


@router.post("/{prompt_id}/render", response_model=RenderResponse)
async def render_prompt(
    prompt_id: uuid.UUID,
    body: RenderRequest,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session),
) -> RenderResponse:
    """블록을 순서대로 이어붙이고 {{변수}}를 주어진 값으로 치환.
    값이 없는 변수는 자리표시자로 남고 missing에 담긴다(렌더는 실패하지 않음)."""
    prompt = await _get_active_prompt(session, workspace, prompt_id)
    blocks = await _load_blocks(session, prompt.id)
    rendered, missing = _render_text(_assemble_text(blocks), body.variables)
    return RenderResponse(rendered=rendered, missing=missing)

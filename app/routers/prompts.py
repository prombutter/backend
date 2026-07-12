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
)

router = APIRouter(prefix="/prompts", tags=["prompts"])

PURGE_AFTER_DAYS = 30  # 소프트 삭제 후 영구 삭제까지 유예
FAVORITE_LIMIT = 5  # 워크스페이스당 즐겨찾기(♥) 상한 (PB-72 확정 정책)

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


async def _detail(session: AsyncSession, prompt: Prompt) -> PromptDetailResponse:
    """프롬프트 + 블록(sort_order 순)을 상세 응답으로 조립."""
    blocks = list(
        await session.scalars(
            select(PromptBlock)
            .where(PromptBlock.prompt_id == prompt.id)
            .order_by(PromptBlock.sort_order)
        )
    )
    return PromptDetailResponse(
        id=prompt.id,
        workspace_id=prompt.workspace_id,
        title=prompt.title,
        favorited_at=prompt.favorited_at,
        created_at=prompt.created_at,
        updated_at=prompt.updated_at,
        blocks=[BlockResponse.model_validate(b) for b in blocks],
    )


@router.post("", response_model=PromptDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    body: PromptCreate,
    workspace: Workspace = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session),
) -> PromptDetailResponse:
    if await _title_taken(session, workspace.id, body.title):
        raise AppError(
            status.HTTP_409_CONFLICT, "ERR-PROMPT-DUP-TITLE", "같은 이름의 프롬프트가 이미 있어요."
        )
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
                "ERR-PROMPT-DUP-TITLE",
                "같은 이름의 프롬프트가 이미 있어요.",
            )
        prompt.title = body.title
        changed = True

    if body.blocks is not None:  # 통째로 교체(생략이면 유지). []면 전부 삭제
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
    """즐겨찾기(♥) 등록. 이미 ♥면 멱등(현재 상태 반환).
    새로 등록 시 워크스페이스 상한(5개) 초과면 409로 차단(자동삭제 X)."""
    prompt = await _get_active_prompt(session, workspace, prompt_id)
    if prompt.favorited_at is not None:  # 이미 등록됨 → 멱등, 상한 검사 불필요
        return prompt
    if await _active_favorite_count(session, workspace.id) >= FAVORITE_LIMIT:
        raise AppError(
            status.HTTP_409_CONFLICT,
            "ERR-FAVORITE-LIMIT",
            f"즐겨찾기는 최대 {FAVORITE_LIMIT}개까지 가능해요. 다른 프롬프트의 즐겨찾기를 먼저 해제해 주세요.",
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
    """즐겨찾기(♥) 해제. 이미 해제 상태여도 멱등(현재 상태 반환)."""
    prompt = await _get_active_prompt(session, workspace, prompt_id)
    if prompt.favorited_at is not None:
        prompt.favorited_at = None
        await session.commit()
        await session.refresh(prompt)
    return prompt

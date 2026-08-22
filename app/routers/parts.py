import re
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.db import get_session
from app.deps import get_path_workspace
from app.models import Workspace
from app.models.parts import Part, Tag, EntityTag
from app.models import Variable
from app.schemas.parts import PartCreate, PartUpdate, PartResponse
from app.core.errors import AppError
router = APIRouter(prefix="/workspaces/{workspace_id}/parts", tags=["Parts"])

async def extract_and_save_variables(session: AsyncSession, entity_id: uuid.UUID, body: str) -> int:
    vars = [v.strip() for v in list(set(re.findall(r"\{\{([\s\S]+?)\}\}", body)))]
    vars = [v for v in vars if v]
    
    if len(vars) > 10:
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "ERR-VAR-002",
            "파츠당 고유 변수는 최대 10개까지만 사용할 수 있어요.",
        )
        
    await session.execute(Variable.__table__.delete().where(
        Variable.entity_id == entity_id,
        Variable.entity_type == 'PART'
    ))
    
    for v in vars:
        new_var = Variable(entity_type='PART', entity_id=entity_id, name=v, has_conflict=False)
        session.add(new_var)
        
    return len(vars)

async def handle_tags(session: AsyncSession, workspace_id: uuid.UUID, entity_id: uuid.UUID, tags: list[str]):
    if not tags:
        tags = []
    tags = list(set([t.lower() for t in tags]))
    
    await session.execute(EntityTag.__table__.delete().where(
        EntityTag.entity_id == entity_id,
        EntityTag.entity_type == 'PART'
    ))
    
    for tag_name in tags:
        stmt = select(Tag).where(Tag.workspace_id == workspace_id, Tag.name == tag_name)
        result = await session.execute(stmt)
        tag = result.scalar_one_or_none()
        if not tag:
            total_tags = await session.scalar(select(func.count()).select_from(Tag).where(Tag.workspace_id == workspace_id))
            if total_tags >= 200:
                raise AppError(status.HTTP_422_UNPROCESSABLE_ENTITY, "ERR-TAG-001", "태그는 워크스페이스당 최대 200개까지만 생성할 수 있어요.")
            tag = Tag(workspace_id=workspace_id, name=tag_name)
            session.add(tag)
            await session.flush()
        
        link = EntityTag(entity_type='PART', entity_id=entity_id, tag_id=tag.id)
        session.add(link)

async def _get_part_with_metadata(session: AsyncSession, part: Part) -> PartResponse:
    # Get variable count
    stmt_vc = select(func.count()).where(Variable.entity_id == part.id, Variable.entity_type == 'PART')
    vc_res = await session.execute(stmt_vc)
    var_count = vc_res.scalar_one()

    # Get tags
    stmt_tags = select(Tag.name).join(EntityTag, Tag.id == EntityTag.tag_id).where(EntityTag.entity_id == part.id)
    tags_res = await session.execute(stmt_tags)
    tags = list(tags_res.scalars().all())

    resp = PartResponse.model_validate(part)
    resp.variable_count = var_count
    resp.tags = tags
    return resp

async def _title_taken(session: AsyncSession, workspace_id: uuid.UUID, title: str, exclude_id: uuid.UUID | None = None) -> bool:
    from app.core.utils import normalize_title
    norm_input = normalize_title(title)
    
    stmt = select(Part.id, Part.title).where(
        Part.workspace_id == workspace_id,
        Part.deleted_at.is_(None)
    )
    if exclude_id is not None:
        stmt = stmt.where(Part.id != exclude_id)
        
    result = await session.execute(stmt)
    for row in result.all():
        if normalize_title(row.title) == norm_input:
            return True
    return False

@router.post("", response_model=PartResponse)
async def create_part(
    part_in: PartCreate, 
    workspace: Workspace = Depends(get_path_workspace),
    session: AsyncSession = Depends(get_session)
):
    if part_in.title:
        part_in.title = re.sub(r'\s+', ' ', part_in.title.strip())

    active_count = await session.scalar(select(func.count()).select_from(Part).where(Part.workspace_id == workspace.id, Part.deleted_at.is_(None)))
    if active_count >= 500:
        raise AppError(status.HTTP_422_UNPROCESSABLE_ENTITY, "ERR-QUOTA-004", "파츠는 계정당 500개까지 만들 수 있어요. 일부를 정리한 뒤 다시 시도해 주세요.")

    # 중복 제목 검사 (정규화 기반)
    if await _title_taken(session, workspace.id, part_in.title):
        raise AppError(status.HTTP_409_CONFLICT, "ERR-PART-001", "이미 동일한 이름의 파츠가 있습니다.")
        
    new_part = Part(
        workspace_id=workspace.id,
        title=part_in.title,
        body=part_in.body
    )
    session.add(new_part)
    await session.flush()
    
    var_count = await extract_and_save_variables(session, new_part.id, part_in.body)
    await handle_tags(session, workspace.id, new_part.id, part_in.tags)
    
    await session.commit()
    await session.refresh(new_part)
    
    resp = PartResponse.model_validate(new_part)
    resp.tags = part_in.tags
    resp.variable_count = var_count
    return resp

@router.post("/{id}/restore", response_model=PartResponse)
async def restore_part(id: uuid.UUID,
    workspace: Workspace = Depends(get_path_workspace),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.id == id, Part.workspace_id == workspace.id, Part.deleted_at.is_not(None))
    result = await session.execute(stmt)
    part = result.scalar_one_or_none()
    if not part:
        raise AppError(status.HTTP_404_NOT_FOUND, "ERR-PART-002", "휴지통에서 파츠를 찾을 수 없습니다.")
        
    part.deleted_at = None
    await session.commit()
    await session.refresh(part)
    return await _get_part_with_metadata(session, part)

@router.delete("/{id}")
async def delete_part(id: uuid.UUID,
    workspace: Workspace = Depends(get_path_workspace),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.id == id, Part.workspace_id == workspace.id, Part.deleted_at.is_(None))
    result = await session.execute(stmt)
    part = result.scalar_one_or_none()
    if not part:
        raise AppError(status.HTTP_404_NOT_FOUND, "ERR-PART-003", "파츠를 찾을 수 없습니다.")
        
    trashed_count = await session.scalar(select(func.count()).select_from(Part).where(Part.workspace_id == workspace.id, Part.deleted_at.is_not(None)))
    if trashed_count >= 200:
        raise AppError(status.HTTP_422_UNPROCESSABLE_ENTITY, "ERR-QUOTA-005", "휴지통 파츠는 계정당 200개까지 보관할 수 있어요. 일부를 영구 삭제한 뒤 다시 시도해 주세요.")
        
    now = datetime.now(timezone.utc)
    part.deleted_at = now
    part.purge_at = now + timedelta(days=30)
    await session.commit()
    return {"success": True, "message": "Part soft-deleted successfully"}

@router.delete("/{id}/permanent")
async def permanent_delete_part(id: uuid.UUID,
    workspace: Workspace = Depends(get_path_workspace),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.id == id, Part.workspace_id == workspace.id, Part.deleted_at.is_not(None))
    result = await session.execute(stmt)
    part = result.scalar_one_or_none()
    if not part:
        raise AppError(status.HTTP_404_NOT_FOUND, "ERR-PART-002", "휴지통에서 파츠를 찾을 수 없습니다.")
        
    await session.execute(EntityTag.__table__.delete().where(EntityTag.entity_id == id, EntityTag.entity_type == 'PART'))
    await session.execute(Variable.__table__.delete().where(Variable.entity_id == id, Variable.entity_type == 'PART'))
    await session.delete(part)
    await session.commit()
    return {"success": True, "message": "Part permanently deleted"}

@router.post("/{id}/favorite", response_model=PartResponse)
async def toggle_favorite_part(
    id: uuid.UUID,
    workspace: Workspace = Depends(get_path_workspace),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.id == id, Part.workspace_id == workspace.id, Part.deleted_at.is_(None))
    result = await session.execute(stmt)
    part = result.scalar_one_or_none()
    if not part:
        raise AppError(status.HTTP_404_NOT_FOUND, "ERR-PART-003", "파츠를 찾을 수 없습니다.")
        
    if not part.is_favorite:
        # 즐겨찾기 추가 시 50개 제한 검사
        fav_count = await session.scalar(select(func.count()).select_from(Part).where(Part.workspace_id == workspace.id, Part.is_favorite == True, Part.deleted_at.is_(None)))
        if fav_count >= 50:
            raise AppError(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "ERR-FAV-001",
                "파츠 즐겨찾기는 50개까지 등록할 수 있어요. 일부를 해제한 뒤 다시 시도해 주세요.",
            )
            
    part.is_favorite = not part.is_favorite
    await session.commit()
    await session.refresh(part)
    return await _get_part_with_metadata(session, part)

@router.get("", response_model=list[PartResponse])
async def list_parts(
    workspace: Workspace = Depends(get_path_workspace),
    is_deleted: bool = Query(False, description="Filter for deleted (trash) items"),
    is_favorite: bool | None = Query(None, description="Filter for favorite items"),
    q: str | None = Query(None, description="Search by title or body"),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.workspace_id == workspace.id)
    if is_deleted:
        stmt = stmt.where(Part.deleted_at.is_not(None))
    else:
        stmt = stmt.where(Part.deleted_at.is_(None))
    
    if is_favorite is not None:
        stmt = stmt.where(Part.is_favorite == is_favorite)
        
    if q:
        stmt = stmt.where(or_(Part.title.ilike(f"%{q}%"), Part.body.ilike(f"%{q}%")))
        
    result = await session.execute(stmt)
    parts = result.scalars().all()
    
    resp_list = []
    for p in parts:
        rp = await _get_part_with_metadata(session, p)
        resp_list.append(rp)
    return resp_list

@router.get("/{id}", response_model=PartResponse)
async def get_part(id: uuid.UUID,
    workspace: Workspace = Depends(get_path_workspace),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.id == id, Part.workspace_id == workspace.id, Part.deleted_at.is_(None))
    result = await session.execute(stmt)
    part = result.scalar_one_or_none()
    if not part:
        raise AppError(status.HTTP_404_NOT_FOUND, "ERR-PART-003", "파츠를 찾을 수 없습니다.")
        
    return await _get_part_with_metadata(session, part)

@router.patch("/{id}", response_model=PartResponse)
async def update_part(id: uuid.UUID,
    part_in: PartUpdate,
    workspace: Workspace = Depends(get_path_workspace),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.id == id, Part.workspace_id == workspace.id, Part.deleted_at.is_(None))
    result = await session.execute(stmt)
    part = result.scalar_one_or_none()
    if not part:
        raise AppError(status.HTTP_404_NOT_FOUND, "ERR-PART-003", "파츠를 찾을 수 없습니다.")
        
    if part_in.title is not None:
        part_in.title = re.sub(r'\s+', ' ', part_in.title.strip())
        if part_in.title != part.title:
            if await _title_taken(session, workspace.id, part_in.title, exclude_id=part.id):
                raise AppError(status.HTTP_409_CONFLICT, "ERR-PART-001", "이미 동일한 이름의 파츠가 있습니다.")
        part.title = part_in.title
    if part_in.body is not None:
        part.body = part_in.body
    if part_in.is_favorite is not None:
        part.is_favorite = part_in.is_favorite
        
    if part_in.body is not None:
        await extract_and_save_variables(session, part.id, part_in.body)
        
    if part_in.tags is not None:
        await handle_tags(session, workspace.id, part.id, part_in.tags)
        
    await session.commit()
    await session.refresh(part)
    
    return await _get_part_with_metadata(session, part)

@router.post("/{id}/duplicate", response_model=PartResponse)
async def duplicate_part(id: uuid.UUID,
    workspace: Workspace = Depends(get_path_workspace),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.id == id, Part.workspace_id == workspace.id, Part.deleted_at.is_(None))
    result = await session.execute(stmt)
    part = result.scalar_one_or_none()
    if not part:
        raise AppError(status.HTTP_404_NOT_FOUND, "ERR-PART-003", "파츠를 찾을 수 없습니다.")
        
    new_part = Part(
        workspace_id=workspace.id,
        title=f"{part.title} (Copy)",
        body=part.body,
        is_favorite=part.is_favorite
    )
    session.add(new_part)
    await session.flush()
    
    await extract_and_save_variables(session, new_part.id, new_part.body)
    
    stmt_tags = select(Tag.name).join(EntityTag, Tag.id == EntityTag.tag_id).where(EntityTag.entity_id == id)
    tags_res = await session.execute(stmt_tags)
    tags = list(tags_res.scalars().all())
    await handle_tags(session, workspace.id, new_part.id, tags)
    
    await session.commit()
    await session.refresh(new_part)
    
    return await _get_part_with_metadata(session, new_part)

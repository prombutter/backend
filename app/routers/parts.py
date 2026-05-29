import re
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db import get_session
from app.models.parts import Part, Tag, EntityTag, Variable
from app.schemas.parts import PartCreate, PartUpdate, PartResponse
from app.api.dependencies import get_current_workspace

router = APIRouter(prefix="/api/v1/parts", tags=["Parts"])

async def extract_and_save_variables(session: AsyncSession, entity_id: uuid.UUID, body: str):
    # Extract {{var}}
    vars = list(set(re.findall(r"\{\{([^}]+)\}\}", body)))
    
    # Delete old
    await session.execute(Variable.__table__.delete().where(
        Variable.entity_id == entity_id,
        Variable.entity_type == 'part'
    ))
    
    # Insert new
    for v in vars:
        new_var = Variable(entity_type='part', entity_id=entity_id, name=v, has_conflict=False)
        session.add(new_var)

async def handle_tags(session: AsyncSession, workspace_id: uuid.UUID, entity_id: uuid.UUID, tags: list[str]):
    # Lowercase and unique
    tags = list(set([t.lower() for t in tags]))
    
    # Delete old entity_tags
    await session.execute(EntityTag.__table__.delete().where(
        EntityTag.entity_id == entity_id,
        EntityTag.entity_type == 'part'
    ))
    
    for tag_name in tags:
        # Check if tag exists
        stmt = select(Tag).where(Tag.workspace_id == workspace_id, Tag.name == tag_name)
        result = await session.execute(stmt)
        tag = result.scalar_one_or_none()
        if not tag:
            tag = Tag(workspace_id=workspace_id, name=tag_name)
            session.add(tag)
            await session.flush()
        
        # Link
        link = EntityTag(entity_type='part', entity_id=entity_id, tag_id=tag.id)
        session.add(link)

@router.post("", response_model=PartResponse)
async def create_part(
    part_in: PartCreate, 
    workspace_id: uuid.UUID = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session)
):
    new_part = Part(
        workspace_id=workspace_id,
        title=part_in.title,
        body=part_in.body
    )
    session.add(new_part)
    await session.flush()
    
    await extract_and_save_variables(session, new_part.id, part_in.body)
    await handle_tags(session, workspace_id, new_part.id, part_in.tags)
    
    await session.commit()
    await session.refresh(new_part)
    
    resp = PartResponse.model_validate(new_part)
    resp.tags = part_in.tags
    return resp

@router.get("", response_model=list[PartResponse])
async def list_parts(
    q: str | None = Query(None, description="Search by title or body"),
    workspace_id: uuid.UUID = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.workspace_id == workspace_id, Part.deleted_at.is_(None))
    
    if q:
        stmt = stmt.where(or_(Part.title.ilike(f"%{q}%"), Part.body.ilike(f"%{q}%")))
        
    result = await session.execute(stmt)
    parts = result.scalars().all()
    
    resp_list = []
    for p in parts:
        rp = PartResponse.model_validate(p)
        rp.tags = [] # Will require eager loading or separate query for efficiency if needed in list
        resp_list.append(rp)
    return resp_list

@router.get("/{id}", response_model=PartResponse)
async def get_part(
    id: uuid.UUID,
    workspace_id: uuid.UUID = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.id == id, Part.workspace_id == workspace_id, Part.deleted_at.is_(None))
    result = await session.execute(stmt)
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
        
    resp = PartResponse.model_validate(part)
    
    # Fetch tags
    stmt_tags = select(Tag.name).join(EntityTag, Tag.id == EntityTag.tag_id).where(EntityTag.entity_id == id)
    tags_res = await session.execute(stmt_tags)
    resp.tags = list(tags_res.scalars().all())
    return resp

@router.put("/{id}", response_model=PartResponse)
async def update_part(
    id: uuid.UUID,
    part_in: PartUpdate,
    workspace_id: uuid.UUID = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.id == id, Part.workspace_id == workspace_id, Part.deleted_at.is_(None))
    result = await session.execute(stmt)
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
        
    if part_in.title is not None:
        part.title = part_in.title
    if part_in.body is not None:
        part.body = part_in.body
    if part_in.is_favorite is not None:
        part.is_favorite = part_in.is_favorite
        
    if part_in.body is not None:
        await extract_and_save_variables(session, part.id, part_in.body)
        
    if part_in.tags is not None:
        await handle_tags(session, workspace_id, part.id, part_in.tags)
        
    await session.commit()
    await session.refresh(part)
    
    resp = PartResponse.model_validate(part)
    stmt_tags = select(Tag.name).join(EntityTag, Tag.id == EntityTag.tag_id).where(EntityTag.entity_id == id)
    tags_res = await session.execute(stmt_tags)
    resp.tags = list(tags_res.scalars().all())
    return resp

@router.delete("/{id}")
async def delete_part(
    id: uuid.UUID,
    workspace_id: uuid.UUID = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.id == id, Part.workspace_id == workspace_id, Part.deleted_at.is_(None))
    result = await session.execute(stmt)
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
        
    part.deleted_at = datetime.now(timezone.utc)
    await session.commit()
    return {"success": True, "message": "Part soft-deleted successfully"}

@router.post("/{id}/duplicate", response_model=PartResponse)
async def duplicate_part(
    id: uuid.UUID,
    workspace_id: uuid.UUID = Depends(get_current_workspace),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Part).where(Part.id == id, Part.workspace_id == workspace_id, Part.deleted_at.is_(None))
    result = await session.execute(stmt)
    part = result.scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
        
    new_part = Part(
        workspace_id=workspace_id,
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
    await handle_tags(session, workspace_id, new_part.id, tags)
    
    await session.commit()
    await session.refresh(new_part)
    
    resp = PartResponse.model_validate(new_part)
    resp.tags = tags
    return resp

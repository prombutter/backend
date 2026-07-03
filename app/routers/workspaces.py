"""
워크스페이스 라우터 — PB-67

GET /workspaces : 본인 워크스페이스 1개 조회 (가입 시 자동 생성된 것).
스코프 트림: 목록/생성/이름수정/멤버 없음 (1:1 자동생성이라 단건).

골격 단계: 시그니처만. 본문은 ③에서 채운다.
위치: app/routers/workspaces.py
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_current_user
from app.models import User, Workspace
from app.schemas import WorkspaceResponse

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=WorkspaceResponse)
async def get_my_workspace(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Workspace:
    ws = await session.scalar(select(Workspace).where(Workspace.owner_id == user.id))
    if ws is None:  # 가입 시 자동 생성되므로 정상 흐름에선 발생 안 함
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return ws

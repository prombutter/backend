import ipaddress
import logging
import re
import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.db import get_session
from app.models import User, UserRole, Workspace
from app.routers.auth import _issue_session
from app.schemas import UserResponse

logger = logging.getLogger(__name__)
DEVELOPER_USER_ID = uuid.uuid5(uuid.NAMESPACE_URL, "prombutter:local-developer")
DEVELOPER_EMAIL = "developer@prombutter.example.com"


def _require_developer_login(request: Request) -> None:
    allowed = settings.is_local_env and settings.DEVELOPER_LOGIN_ENABLED
    host = request.client.host if request.client else ""
    try:
        allowed = allowed and ipaddress.ip_address(host).is_loopback
    except ValueError:
        allowed = False
    allowed = allowed and request.url.hostname in {"localhost", "127.0.0.1", "::1"}
    allowed = allowed and not any(
        name == "forwarded" or name.startswith("x-forwarded-") for name in request.headers
    )
    allowed = allowed and request.headers.get("x-requested-with") == "Prombutter-Extension"
    origin = request.headers.get("origin")
    if origin is not None:
        allowed = allowed and re.fullmatch(r"chrome-extension://[a-p]{32}", origin) is not None
    if not allowed:
        logger.info("developer_login result=blocked reason=local_policy")
        raise AppError(
            status.HTTP_403_FORBIDDEN,
            "ERR-AUTH-DEV-001",
            "개발자 로그인은 활성화된 로컬 개발 환경에서만 사용할 수 있어요.",
        )


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/developer-login",
    response_model=UserResponse,
    dependencies=[Depends(_require_developer_login)],
)
async def developer_login(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> User:
    # 고정된 개발 전용 계정만 사용하고, 동시 클릭에도 계정과 워크스페이스는 하나만 만든다.
    await session.execute(
        insert(User)
        .values(
            id=DEVELOPER_USER_ID,
            email=DEVELOPER_EMAIL,
            name="Developer",
            role=UserRole.USER,
        )
        .on_conflict_do_nothing()
    )
    user = await session.get(User, DEVELOPER_USER_ID)
    if (
        user is None
        or user.email != DEVELOPER_EMAIL
        or user.role != UserRole.USER
        or user.password_hash is not None
    ):
        raise AppError(
            status.HTTP_409_CONFLICT,
            "ERR-AUTH-DEV-002",
            "개발용 계정 설정을 확인해 주세요.",
        )
    await session.execute(
        insert(Workspace)
        .values(owner_id=user.id, name="Developer workspace")
        .on_conflict_do_nothing(index_elements=[Workspace.owner_id])
    )
    await _issue_session(session, user, response)
    await session.commit()
    await session.refresh(user)
    logger.info("developer_login result=success user_id=%s", user.id)
    return user

import logging
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.core.config import settings
from app.batch.hard_delete import run_hard_delete

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/batch", tags=["Batch"])

async def verify_batch_token(x_batch_token: str = Header(...)):
    if x_batch_token != settings.SECRET_KEY:
        logger.warning("Unauthorized batch execution attempt.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid batch token"
        )
    return True

@router.post("/hard-delete", dependencies=[Depends(verify_batch_token)])
async def trigger_hard_delete(session: AsyncSession = Depends(get_session)):
    try:
        await run_hard_delete(session)
        return {"success": True, "message": "Hard delete batch executed successfully"}
    except Exception as e:
        logger.error(f"Batch execution failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch execution failed"
        )

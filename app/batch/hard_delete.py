import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete

from app.db import SessionLocal
from app.models import (
    Prompt,
    PromptBlock,
    Variable,
)
from app.models.parts import Part, EntityTag

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def run_hard_delete(session=None):
    logger.info("Starting hard delete batch job...")
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    
    if session:
        await _execute_hard_delete(session, cutoff)
    else:
        async with SessionLocal() as db_session:
            await _execute_hard_delete(db_session, cutoff)

async def _execute_hard_delete(session, cutoff):
    try:
        # 1. 대상 파츠(Parts) 조회
        parts_stmt = select(Part.id).where(Part.deleted_at < cutoff)
        parts_result = await session.execute(parts_stmt)
        part_ids = parts_result.scalars().all()
        
        # 2. 대상 프롬프트(Prompts) 조회
        prompts_stmt = select(Prompt.id).where(Prompt.deleted_at < cutoff)
        prompts_result = await session.execute(prompts_stmt)
        prompt_ids = prompts_result.scalars().all()
        
        deleted_parts_count = 0
        deleted_prompts_count = 0
        
        if part_ids:
            logger.info(f"Found {len(part_ids)} parts to hard delete.")
            # 연관 Variable 삭제 (다형성)
            await session.execute(delete(Variable).where(Variable.entity_id.in_(part_ids), Variable.entity_type == 'PART'))
            # 연관 EntityTag 삭제 (다형성)
            await session.execute(delete(EntityTag).where(EntityTag.entity_id.in_(part_ids), EntityTag.entity_type == 'PART'))
            # Part 삭제
            res = await session.execute(delete(Part).where(Part.id.in_(part_ids)))
            deleted_parts_count = res.rowcount

        if prompt_ids:
            logger.info(f"Found {len(prompt_ids)} prompts to hard delete.")
            # 연관 Variable 삭제 (다형성)
            await session.execute(delete(Variable).where(Variable.entity_id.in_(prompt_ids), Variable.entity_type == 'PROMPT'))
            # 연관 EntityTag 삭제 (다형성)
            await session.execute(delete(EntityTag).where(EntityTag.entity_id.in_(prompt_ids), EntityTag.entity_type == 'PROMPT'))
            # 연관 PromptBlock 삭제
            await session.execute(delete(PromptBlock).where(PromptBlock.prompt_id.in_(prompt_ids)))
            # Prompt 삭제
            res = await session.execute(delete(Prompt).where(Prompt.id.in_(prompt_ids)))
            deleted_prompts_count = res.rowcount
            
        await session.commit()
        logger.info(f"Batch job finished successfully. Deleted {deleted_parts_count} parts and {deleted_prompts_count} prompts.")
    except Exception as e:
        await session.rollback()
        logger.error(f"Error during hard delete batch job: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_hard_delete())

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete

from app.db import SessionLocal
from app.models import (
    Prompt,
    PromptBlock,
    Variable,
    BlockType,
)
from app.models.parts import Part, EntityTag

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def run_hard_delete(session=None):
    logger.info("Starting hard delete batch job...")
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    
    if session:
        await _execute_hard_delete(session, cutoff, now)
    else:
        async with SessionLocal() as db_session:
            await _execute_hard_delete(db_session, cutoff, now)

async def _execute_hard_delete(session, cutoff, now):
    try:
        # 1. 대상 프롬프트(Prompts) 조회 — 프롬프트를 먼저 삭제해야 블록의 FK(→parts) 해소
        prompts_stmt = select(Prompt.id).where(
            Prompt.deleted_at.is_not(None),
            ((Prompt.purge_at <= now) | ((Prompt.purge_at.is_(None)) & (Prompt.deleted_at < cutoff)))
        )
        prompts_result = await session.execute(prompts_stmt)
        prompt_ids = prompts_result.scalars().all()

        # 2. 대상 파츠(Parts) 조회 — deleted_at IS NOT NULL 필수(복원된 항목 보호)
        parts_stmt = select(Part.id).where(
            Part.deleted_at.is_not(None),
            ((Part.purge_at <= now) | ((Part.purge_at.is_(None)) & (Part.deleted_at < cutoff)))
        )
        parts_result = await session.execute(parts_stmt)
        part_ids = parts_result.scalars().all()
        
        deleted_parts_count = 0
        deleted_prompts_count = 0

        # 프롬프트를 먼저 삭제 (prompt_blocks.part_id FK 해소)
        if prompt_ids:
            logger.info(f"Found {len(prompt_ids)} prompts to hard delete.")
            await session.execute(delete(Variable).where(Variable.entity_id.in_(prompt_ids), Variable.entity_type == 'PROMPT'))
            await session.execute(delete(EntityTag).where(EntityTag.entity_id.in_(prompt_ids), EntityTag.entity_type == 'PROMPT'))
            await session.execute(delete(PromptBlock).where(PromptBlock.prompt_id.in_(prompt_ids)))
            res = await session.execute(delete(Prompt).where(Prompt.id.in_(prompt_ids)))
            deleted_prompts_count = res.rowcount

        # 파츠 삭제 (참조 중인 블록은 INLINE 텍스트로 변환하여 본문 보존 후 삭제)
        if part_ids:
            logger.info(f"Found {len(part_ids)} parts to hard delete.")
            
            # 1. 삭제할 파츠들의 본문 조회
            parts_to_delete = (await session.execute(select(Part.id, Part.body).where(Part.id.in_(part_ids)))).all()
            part_body_map = {row.id: row.body for row in parts_to_delete}
            
            # 2. 참조 중인 프롬프트 블록 찾아서 인라인으로 변환
            blocks = (await session.execute(select(PromptBlock).where(PromptBlock.part_id.in_(part_ids)))).scalars().all()
            for block in blocks:
                block.block_type = BlockType.INLINE
                block.inline_body = part_body_map.get(block.part_id, "")
                block.part_id = None
                
            # 3. 일괄 삭제 진행
            safe_ids = part_ids
            if safe_ids:
                await session.execute(delete(Variable).where(Variable.entity_id.in_(safe_ids), Variable.entity_type == 'PART'))
                await session.execute(delete(EntityTag).where(EntityTag.entity_id.in_(safe_ids), EntityTag.entity_type == 'PART'))
                res = await session.execute(delete(Part).where(Part.id.in_(safe_ids)))
                deleted_parts_count = res.rowcount
            
        await session.commit()
        logger.info(f"Batch job finished successfully. Deleted {deleted_parts_count} parts and {deleted_prompts_count} prompts.")
    except Exception as e:
        await session.rollback()
        logger.error(f"Error during hard delete batch job: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_hard_delete())

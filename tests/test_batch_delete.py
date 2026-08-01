import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.models import Prompt, Variable, PromptBlock
from app.db import SessionLocal
from app.batch.hard_delete import run_hard_delete

import pytest_asyncio

@pytest_asyncio.fixture
async def async_session():
    async with SessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def default_workspace(async_session, test_workspace_id):
    from app.models import Workspace
    ws = await async_session.get(Workspace, test_workspace_id)
    return ws

pytestmark = pytest.mark.asyncio

async def test_hard_delete_removes_old_data(async_session, default_workspace):
    now = datetime.now(timezone.utc)
    
    # 1. 40일 전에 삭제된 파츠 (Hard Delete 대상)
    old_part = Part(
        id=uuid.uuid4(),
        workspace_id=default_workspace.id,
        title="Old Part",
        body="{{var1}}",
        deleted_at=now - timedelta(days=40)
    )
    async_session.add(old_part)
    
    # 2. 10일 전에 삭제된 파츠 (Hard Delete 대상 아님)
    recent_part = Part(
        id=uuid.uuid4(),
        workspace_id=default_workspace.id,
        title="Recent Part",
        body="{{var2}}",
        deleted_at=now - timedelta(days=10)
    )
    async_session.add(recent_part)
    
    # 3. 40일 전에 삭제된 프롬프트 (Hard Delete 대상)
    old_prompt = Prompt(
        id=uuid.uuid4(),
        workspace_id=default_workspace.id,
        title="Old Prompt",
        deleted_at=now - timedelta(days=40)
    )
    async_session.add(old_prompt)
    
    # 4. 종속 데이터 추가
    old_var = Variable(entity_type='PART', entity_id=old_part.id, name='var1')
    old_tag = EntityTag(entity_type='PROMPT', entity_id=old_prompt.id, tag='test')
    old_block = PromptBlock(prompt_id=old_prompt.id, sort_order=1, block_type='INLINE', inline_body='test block')
    async_session.add_all([old_var, old_tag, old_block])
    
    await async_session.commit()

    # 배치 스크립트 실행
    # (테스트 환경에서는 _session_maker가 연결된 별도의 세션을 사용하므로 
    # run_hard_delete 에 직접 넘겨줌)
    await run_hard_delete(session=async_session)
    
    # 결과 확인
    # old_part 와 old_prompt 는 삭제되어야 함
    part1 = await async_session.get(Part, old_part.id)
    assert part1 is None
    
    prompt1 = await async_session.get(Prompt, old_prompt.id)
    assert prompt1 is None
    
    # recent_part 는 남아있어야 함
    part2 = await async_session.get(Part, recent_part.id)
    assert part2 is not None
    
    # 종속 데이터들도 삭제되어야 함
    var_res = await async_session.scalar(select(Variable).where(Variable.entity_id == old_part.id))
    assert var_res is None
    
    tag_res = await async_session.scalar(select(EntityTag).where(EntityTag.entity_id == old_prompt.id))
    assert tag_res is None
    
    block_res = await async_session.scalar(select(PromptBlock).where(PromptBlock.prompt_id == old_prompt.id))
    assert block_res is None

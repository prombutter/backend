from fastapi import APIRouter
from app.core.responses import success
from datetime import datetime, timezone

router = APIRouter(prefix="/prompts", tags=["Prompts"])

MOCK_PROMPTS = [
    {
        "id": "prompt_001",
        "title": "SEO 최적화 블로그 작성기",
        "content": "이 프롬프트는 SEO에 최적화된 글을 작성합니다. {{keyword}}를 주제로 작성해주세요.",
        "tags": ["seo", "blog"],
        "is_favorite": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
]

@router.get("")
async def get_prompts():
    return success({
        "items": MOCK_PROMPTS,
        "total": len(MOCK_PROMPTS),
        "page": 1,
        "size": 10
    })

@router.post("")
async def create_prompt():
    new_prompt = MOCK_PROMPTS[0].copy()
    new_prompt["id"] = "prompt_new_123"
    return success(new_prompt)

@router.get("/{id}")
async def get_prompt(id: str):
    return success(MOCK_PROMPTS[0])

@router.put("/{id}")
async def update_prompt(id: str):
    updated = MOCK_PROMPTS[0].copy()
    updated["title"] = "수정된 프롬프트 제목"
    return success(updated)

@router.delete("/{id}")
async def delete_prompt(id: str):
    return success({"message": f"Prompt {id} soft-deleted successfully"})

@router.post("/{id}/favorite")
async def add_favorite(id: str):
    return success({"message": f"Prompt {id} added to favorites"})

@router.delete("/{id}/favorite")
async def remove_favorite(id: str):
    return success({"message": f"Prompt {id} removed from favorites"})

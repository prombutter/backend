from fastapi import APIRouter
from app.core.responses import success
from datetime import datetime, timezone

router = APIRouter(prefix="/parts", tags=["Parts"])

MOCK_PARTS = [
    {
        "id": "part_001",
        "title": "마케팅 전문가 페르소나",
        "content": "Act as a Growth Marketing expert. Your goal is to generate a marketing copy for: {{product_name}}.",
        "tags": ["marketing", "persona"],
        "is_favorite": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "part_002",
        "title": "블로그 포스트 스타일",
        "content": "아래 내용을 정리해줘. {{tone}}한 어조로 작성해.",
        "tags": ["blog", "style"],
        "is_favorite": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
]

@router.get("")
async def get_parts():
    return success({
        "items": MOCK_PARTS,
        "total": len(MOCK_PARTS),
        "page": 1,
        "size": 10
    })

@router.post("")
async def create_part():
    new_part = MOCK_PARTS[0].copy()
    new_part["id"] = "part_new_123"
    return success(new_part)

@router.get("/{id}")
async def get_part(id: str):
    return success(MOCK_PARTS[0])

@router.put("/{id}")
async def update_part(id: str):
    updated_part = MOCK_PARTS[0].copy()
    updated_part["title"] = "수정된 파츠 제목"
    return success(updated_part)

@router.delete("/{id}")
async def delete_part(id: str):
    return success({"message": f"Part {id} soft-deleted successfully"})

@router.post("/{id}/duplicate")
async def duplicate_part(id: str):
    dup_part = MOCK_PARTS[0].copy()
    dup_part["id"] = f"{id}_copy"
    dup_part["title"] = f"{dup_part['title']} (Copy)"
    return success(dup_part)

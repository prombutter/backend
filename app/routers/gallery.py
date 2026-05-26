from fastapi import APIRouter
from app.core.responses import success

router = APIRouter(prefix="/gallery", tags=["Gallery"])

MOCK_GALLERY_SAMPLES = [
    {
        "id": "gallery_001",
        "category": "Marketing",
        "title": "스타트업 랜딩페이지 카피라이팅",
        "description": "전환율을 높이는 깔끔한 카피를 작성합니다.",
        "usage_count": 1250,
        "author": "Official"
    },
    {
        "id": "gallery_002",
        "category": "Development",
        "title": "Python 코드 리뷰어",
        "description": "클린 코드 원칙에 따라 코드를 리뷰해 줍니다.",
        "usage_count": 980,
        "author": "Official"
    }
]

@router.get("/samples")
async def get_gallery_samples():
    return success({
        "items": MOCK_GALLERY_SAMPLES,
        "total": len(MOCK_GALLERY_SAMPLES)
    })

@router.post("/copy/{id}")
async def copy_from_gallery(id: str):
    return success({
        "message": f"Gallery item {id} copied to your workspace successfully.",
        "new_prompt_id": "prompt_copied_123"
    })

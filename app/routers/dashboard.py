from fastapi import APIRouter
from app.core.responses import success

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/usage")
async def get_dashboard_usage():
    return success({
        "total_injections": 142,
        "top_prompts": [
            {"id": "prompt_001", "title": "SEO 최적화 블로그 작성기", "count": 45},
            {"id": "part_001", "title": "마케팅 전문가 페르소나", "count": 32}
        ]
    })

@router.get("/tags")
async def get_dashboard_tags():
    return success({
        "tags": [
            {"name": "marketing", "count": 15},
            {"name": "blog", "count": 10},
            {"name": "seo", "count": 8}
        ]
    })

@router.get("/cold-start")
async def check_cold_start():
    return success({
        "is_new_user": False,
        "message": "User has existing parts and prompts."
    })

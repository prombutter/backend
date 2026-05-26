from fastapi import APIRouter
from app.core.responses import success

router = APIRouter(prefix="/extension", tags=["Extension"])

@router.get("/config")
async def get_extension_config():
    return success({
        "target_domains": [
            "chatgpt.com",
            "claude.ai",
            "gemini.google.com"
        ],
        "selectors": {
            "chatgpt.com": "textarea[data-id='root']",
            "claude.ai": "div.ProseMirror",
            "gemini.google.com": "rich-textarea"
        }
    })

@router.get("/fetch/{id}")
async def fetch_injection_text(id: str):
    return success({
        "id": id,
        "injected_text": "Act as a Growth Marketing expert. Your goal is to generate a marketing copy for: [Product Name]. \n\n이 프롬프트는 SEO에 최적화된 글을 작성합니다."
    })

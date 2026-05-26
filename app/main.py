from datetime import datetime, timezone
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, parts, prompts, gallery, dashboard, extension
try:
    from app.routers import health
except ImportError:
    health = None

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if health:
    app.include_router(health.router)

api_router = APIRouter(prefix=settings.API_V1_STR)
api_router.include_router(auth.router)
api_router.include_router(parts.router)
api_router.include_router(prompts.router)
api_router.include_router(gallery.router)
api_router.include_router(dashboard.router)
api_router.include_router(extension.router)

app.include_router(api_router)

@app.get("/")
async def root():
    return {
        "success": True,
        "data": {
            "message": "Welcome to PromptOps API",
            "service": "prombutter-backend"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "success": True,
        "data": {"status": "healthy"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

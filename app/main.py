from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import AppError, app_error_handler, validation_error_handler
from app.routers import auth, prompts, workspaces
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

# 에러 응답 형식 통일 (PB-72 확정 정책: error_code + message)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

if health:
    app.include_router(health.router)
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(prompts.router)

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

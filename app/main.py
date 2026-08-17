from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import AppError, app_error_handler, validation_error_handler
from app.routers import auth, oauth, parts, prompts, workspaces
try:
    from app.routers import health
except ImportError:
    health = None

_docs = settings.is_local_env
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if _docs else None,
    docs_url="/docs" if _docs else None,
    redoc_url="/redoc" if _docs else None,
)

# Set all CORS enabled origins
_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if any(origin == "*" for origin in _cors_origins):
    raise RuntimeError("CORS_ORIGINS=* is not allowed")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With", "X-CSRF-Token"],
)

# 에러 응답 형식 통일 (PB-72 확정 정책: error_code + message)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

if health:
    app.include_router(health.router)
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(workspaces.router)
app.include_router(prompts.router)
app.include_router(parts.router, prefix="/api/v1")

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

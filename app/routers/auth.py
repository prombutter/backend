from fastapi import APIRouter
from app.core.responses import success

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/signup")
async def signup():
    return success({
        "user_id": "usr_12345",
        "email": "nam_kyung@example.com",
        "name": "nam_kyung",
        "access_token": "mock_jwt_access_token_123",
        "refresh_token": "mock_jwt_refresh_token_456"
    })

@router.post("/login")
async def login():
    return success({
        "user_id": "usr_12345",
        "email": "nam_kyung@example.com",
        "name": "nam_kyung",
        "access_token": "mock_jwt_access_token_123",
        "refresh_token": "mock_jwt_refresh_token_456"
    })

@router.post("/oauth/google")
async def oauth_google():
    return success({
        "user_id": "usr_12345",
        "email": "nam_kyung@example.com",
        "name": "nam_kyung",
        "access_token": "mock_jwt_access_token_123",
        "refresh_token": "mock_jwt_refresh_token_456"
    })

@router.post("/extension/sync")
async def extension_sync():
    return success({
        "session_id": "sess_7890",
        "device_id": "dev_abcde"
    })

@router.post("/logout")
async def logout():
    return success({"message": "Successfully logged out"})

@router.put("/settings")
async def update_settings():
    return success({"message": "Settings updated successfully", "name": "nam_kyung_new"})

@router.delete("/withdraw")
async def withdraw():
    return success({"message": "Account deleted successfully"})

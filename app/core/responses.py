from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar('DataT')

class SuccessResponse(BaseModel, Generic[DataT]):
    success: bool = True
    data: DataT
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

def success(data: Any) -> dict:
    return {
        "success": True,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def error(code: str, message: str) -> dict:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

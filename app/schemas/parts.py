import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class PartBase(BaseModel):
    title: str = Field(..., max_length=100)
    body: str = Field(..., max_length=700)
    tags: List[str] = Field(default_factory=list, max_length=10)

class PartCreate(PartBase):
    pass

class PartUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    body: Optional[str] = Field(None, max_length=700)
    tags: Optional[List[str]] = Field(None, max_length=10)
    is_favorite: Optional[bool] = None

class PartResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    body: str
    is_favorite: bool
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

import uuid
from datetime import datetime
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field

class PartBase(BaseModel):
    title: str = Field(..., max_length=100)
    body: str = Field(..., max_length=700)
    tags: List[Annotated[str, Field(max_length=30)]] = Field(default_factory=list, max_length=10)

class PartCreate(PartBase):
    pass

class PartUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    body: Optional[str] = Field(None, max_length=700)
    tags: Optional[List[Annotated[str, Field(max_length=30)]]] = Field(None, max_length=10)
    is_favorite: Optional[bool] = None

class PartResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    title: str
    body: str
    is_favorite: bool
    variable_count: int = 0
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SupabaseTokenExchangeRequest(BaseModel):
    """SPA 가 Supabase OAuth 로 받은 access_token 을 앱 세션으로 교환."""

    access_token: str = Field(min_length=20, description="Supabase Auth access_token (JWT)")
    refresh_token: str | None = Field(
        default=None,
        description="Supabase refresh_token (선택, 보관용)",
    )
    provider_token: str | None = Field(
        default=None,
        description="Google provider access token (Revoke 용, 있으면 저장)",
    )
    provider_refresh_token: str | None = None
    device_info: str | None = Field(default=None, max_length=500)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)
    device_info: str | None = Field(default=None, max_length=500)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    refresh_expires_at: datetime
    is_new_user: bool
    user: "UserPublic"


class UserPublic(BaseModel):
    id: UUID
    email: str
    name: str
    role: str
    workspace_id: UUID | None = None
    onboarding_completed: bool = False


class OAuthStartResponse(BaseModel):
    authorize_url: str
    provider: str
    state_cookie: str = "pb_oauth_state"

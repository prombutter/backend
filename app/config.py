from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PRODUCTION_ENVS = {"production", "prod", "staging"}


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/prombutter"

    # --- Supabase API (Auth OAuth + optional admin) ---
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # --- App JWT session ---
    jwt_secret: str = "change-me-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # Fernet key (url-safe base64 32-byte). 미설정 시 provider 토큰은 DB 에 저장하지 않음
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    oauth_token_key: str = ""

    # OAuth 콜백·FE 복귀 URL
    # Supabase Dashboard → Authentication → URL Configuration 에 등록 필수
    oauth_callback_url: str = "http://localhost:8000/auth/oauth/callback"
    oauth_frontend_redirect: str = "http://localhost:3000/auth/callback"
    # 허용 FE 리다이렉트 (CSV). 비우면 oauth_frontend_redirect 단일만 허용
    oauth_allowed_redirects: str = "http://localhost:3000"

    app_env: str = "development"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    allowed_hosts: str = "localhost,127.0.0.1"

    # --- DB pool limits ---
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        origins = split_csv(self.cors_origins)
        return [o for o in origins if o != "*"]

    @property
    def allowed_host_list(self) -> list[str]:
        return split_csv(self.allowed_hosts)

    @property
    def is_production_like(self) -> bool:
        return self.app_env.strip().lower() in PRODUCTION_ENVS

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def supabase_configured_for_oauth(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def oauth_frontend_redirect_list(self) -> list[str]:
        items = split_csv(self.oauth_allowed_redirects)
        if self.oauth_frontend_redirect and self.oauth_frontend_redirect not in items:
            items.append(self.oauth_frontend_redirect)
        return items

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if not self.is_production_like:
            return self

        cors_origins = split_csv(self.cors_origins)
        if not cors_origins or "*" in cors_origins:
            raise ValueError("CORS_ORIGINS must be explicit in production/staging.")
        if any(not origin.startswith("https://") for origin in cors_origins):
            raise ValueError("CORS_ORIGINS must use https:// in production/staging.")

        hosts = self.allowed_host_list
        local_hosts = {"localhost", "127.0.0.1", "::1"}
        if not hosts or "*" in hosts or any(host in local_hosts for host in hosts):
            raise ValueError("ALLOWED_HOSTS must be explicit public hostnames in production/staging.")
        if any("://" in host for host in hosts):
            raise ValueError("ALLOWED_HOSTS must contain hostnames only, not URL origins.")

        parsed = urlparse(self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1))
        if (parsed.hostname or "") in {"", "localhost", "127.0.0.1", "::1"}:
            raise ValueError("DATABASE_URL must not point to a local database in production/staging.")
        if "postgres:password@" in self.database_url:
            raise ValueError("DATABASE_URL must not use the example password in production/staging.")

        if self.jwt_secret in {"", "change-me-use-openssl-rand-hex-32"}:
            raise ValueError("JWT_SECRET must be set to a strong secret in production/staging.")

        if not self.supabase_configured_for_oauth:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY are required in production/staging.")

        return self


settings = Settings()

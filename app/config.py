from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PRODUCTION_ENVS = {"production", "prod", "staging"}


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/prombutter"

    # --- Supabase API (optional; DB connection uses database_url above) ---
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

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
        # Wildcard CORS 차단 — 명시적 출처만 허용
        return [o for o in origins if o != "*"]

    @property
    def allowed_host_list(self) -> list[str]:
        return split_csv(self.allowed_hosts)

    @property
    def is_production_like(self) -> bool:
        return self.app_env.strip().lower() in PRODUCTION_ENVS

    @property
    def supabase_configured(self) -> bool:
        # service_role 키는 서버 측 Supabase 클라이언트(Storage·Admin·RPC 등) 사용 전제
        return bool(self.supabase_url and self.supabase_service_role_key)

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

        return self


settings = Settings()

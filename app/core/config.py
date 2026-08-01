from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    PROJECT_NAME: str = "Prombutter"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # --- Security / Auth ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # AT 1시간
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # RT 7일
    BCRYPT_ROUNDS: int = 12
    COOKIE_SECURE: bool = False

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/dbname"

    # --- Supabase (Auth OAuth + optional admin) ---
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # provider 토큰 DB 암호화 (Fernet). 미설정 시 provider 토큰 미저장
    OAUTH_TOKEN_KEY: str = ""
    OAUTH_CALLBACK_URL: str = "http://localhost:8000/auth/oauth/callback"
    OAUTH_FRONTEND_REDIRECT: str = "http://localhost:3000/auth/callback"
    OAUTH_ALLOWED_REDIRECTS: str = "http://localhost:3000"

    # --- GCP ---
    GCP_PROJECT_ID: str | None = None
    GCP_STORAGE_BUCKET: str | None = None

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def supabase_oauth_ready(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_ANON_KEY)

    @property
    def oauth_frontend_redirect_list(self) -> list[str]:
        items = _split_csv(self.OAUTH_ALLOWED_REDIRECTS)
        if self.OAUTH_FRONTEND_REDIRECT and self.OAUTH_FRONTEND_REDIRECT not in items:
            items.append(self.OAUTH_FRONTEND_REDIRECT)
        return items


settings = Settings()

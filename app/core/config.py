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
    APP_ENV: str = "local"
    # 비밀번호 재설정 토큰을 콘솔에 찍을지. 이메일 발송이 아직 없어 개발 중에는 이것이 유일한
    # 전달 경로지만, 운영에서 stdout 은 곧 로그 수집기다. 로그 열람 권한이 계정 탈취 경로가
    # 되지 않도록 기본은 꺼 둔다 — 켜는 것은 개발자가 명시할 때만이다.
    EXPOSE_RESET_TOKEN: bool = False

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
    def is_local_env(self) -> bool:
        return self.APP_ENV.lower() in {"local", "dev", "development"}

    @property
    def cookie_secure_effective(self) -> bool:
        if self.COOKIE_SECURE:
            return True
        return any(origin.strip().startswith("https://") for origin in self.CORS_ORIGINS.split(","))

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

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Prombutter"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # --- Security / Auth ---
    SECRET_KEY: str = "supersecretkey"  # ⚠️ 운영에선 반드시 .env에서 강한 랜덤값으로 덮어쓸 것
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60      # AT 1시간
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080    # RT 7일
    BCRYPT_ROUNDS: int = 12
    COOKIE_SECURE: bool = False

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/dbname"

    # --- GCP ---
    GCP_PROJECT_ID: str | None = None
    GCP_STORAGE_BUCKET: str | None = None

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
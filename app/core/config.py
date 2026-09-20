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
    # 쿠키 SameSite. FE 와 API 가 다른 사이트면(예: *.vercel.app ↔ *.run.app) "none" 이라야
    # 로그인 세션이 전송된다. 익스텐션은 chatgpt.com 컨텍스트라 어떤 구성에서도 크로스 사이트다.
    COOKIE_SAMESITE: str = "lax"
    # 하위 도메인 공유가 필요할 때만 지정한다(예: ".prombutter.com").
    # 빈 값이면 응답한 호스트에만 묶인다.
    COOKIE_DOMAIN: str = ""
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

    # --- Email (SendGrid) ---
    SENDGRID_API_KEY: str = ""
    MAIL_FROM_ADDRESS: str = "noreply@prombutter.com"

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
        if not self.is_local_env:
            return True
        return any(origin.strip().startswith("https://") for origin in self.CORS_ORIGINS.split(","))

    @property
    def cookie_samesite_effective(self) -> str:
        """SameSite 값을 정규화해서 돌려준다.

        브라우저는 Secure 없는 SameSite=None 쿠키를 그냥 버린다. 그래서 두 값이 어긋나면
        증상이 "쿠키가 안 실린다"로만 나타나고 원인은 응답 헤더를 뜯어보기 전엔 안 보인다.
        설정 단계에서 막는다.
        """
        value = (self.COOKIE_SAMESITE or "lax").strip().lower()
        if value not in {"lax", "strict", "none"}:
            raise RuntimeError(
                f"COOKIE_SAMESITE 는 lax·strict·none 중 하나여야 합니다 (받은 값: {self.COOKIE_SAMESITE!r})"
            )
        if value == "none" and not self.cookie_secure_effective:
            raise RuntimeError(
                "COOKIE_SAMESITE=none 은 COOKIE_SECURE=true 와 함께여야 합니다 "
                "(Secure 없는 SameSite=None 쿠키는 브라우저가 거부합니다)"
            )
        return value

    @property
    def cookie_domain_effective(self) -> str | None:
        return self.COOKIE_DOMAIN.strip() or None

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

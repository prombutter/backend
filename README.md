# PromButter Backend

FastAPI 기반 **DB 세팅·연결·SQL 전달용** 백엔드. PostgreSQL(Supabase) 사용.

> 이 레포는 **DB 스키마 셋업과 SQL 전달**이 목적이며, 서비스로 **배포하지 않는다.**
> 포함된 FastAPI 앱은 로컬에서 DB 연결을 확인(`/db-ping`)하기 위한 경량 도구다.

## DB 스키마 / 마이그레이션

- 빈 DB 최초 설치: `db/migrations/0001_init.sql` 를 그대로 실행한다 (확장 `citext`·`pgcrypto` + enum 타입 + 전체 테이블/인덱스/FK 포함 — 빈 DB 에 한 번에 설치 가능).
- 이후 스키마 변경 관리 규칙: [db/README.md](db/README.md) 참조.

```powershell
# 예: psql 로 빈 DB 에 설치
psql "<DATABASE_URL>" -f db/migrations/0001_init.sql
# 또는 Supabase Dashboard → SQL Editor 에 파일 내용 붙여넣기
```

## 로컬 실행 (DB 연결 확인용)

### 1. uv 설치 (1회)

```powershell
# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 의존성 설치

```powershell
uv sync
```

### 3. 환경 변수

```powershell
copy .env.example .env
# .env 의 DATABASE_URL 을 Supabase Connection string 으로 교체
```

### 4. 서버 실행

```powershell
uv run uvicorn app.main:app --reload --port 8000
```

- http://localhost:8000/        → 서비스 정보
- http://localhost:8000/health  → 헬스체크
- http://localhost:8000/db-ping → DB 연결 확인
- http://localhost:8000/docs    → Swagger UI

## Supabase 설정

1. https://supabase.com/dashboard 에서 New Project
2. Database Password 설정 (안전한 곳에 보관)
3. **Project Settings → Database → Connection string → URI** 복사
4. URI 의 `postgresql://` 를 `postgresql+asyncpg://` 로 교체하여 `.env` 의 `DATABASE_URL` 에 붙여넣기
5. Pooler(6543) 사용 권장 — 서버리스 환경에서 안정적
6. **Project Settings → API** 에서 `SUPABASE_URL` · `anon` · `service_role` 키를 `.env` 에 설정

## Supabase Google OAuth

앱은 **Supabase Auth 가 Google OAuth 를 수행**하고, 콜백/토큰 교환 후
로컬 `users` · `user_identities(provider=GOOGLE)` · `workspaces` · `user_sessions` 에 연동한 뒤
**앱 자체 JWT** 를 발급한다.

### Dashboard 설정

1. **Authentication → Providers → Google** 활성화  
   - Google Cloud Console OAuth 2.0 Client ID/Secret 등록  
   - Authorized redirect URI 에 Supabase 콜백 추가  
     `https://<project-ref>.supabase.co/auth/v1/callback`
2. **Authentication → URL Configuration**  
   - Site URL: FE 주소 (예: `http://localhost:3000`)  
   - Additional Redirect URLs:
     - `http://localhost:8000/auth/oauth/callback` (백엔드 PKCE 콜백)
     - `http://localhost:3000/auth/callback` (FE SPA 직접 플로우)
3. DB 마이그레이션 `0001_init.sql` + `0002_add_unique_constraints.sql` 적용

### 플로우 A — 백엔드 리다이렉트 (브라우저)

```
GET  /auth/oauth/google/redirect?redirect_uri=http://localhost:3000/auth/callback
  → Supabase Google 로그인
  → GET /auth/oauth/callback?code=...
  → 302 FE#access_token=...&refresh_token=...
```

### 플로우 B — FE Supabase SDK (권장 SPA)

```js
const { data } = await supabase.auth.signInWithOAuth({ provider: 'google' })
// 콜백 후
const { data: { session } } = await supabase.auth.getSession()
await fetch('http://localhost:8000/auth/oauth/supabase', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    access_token: session.access_token,
    refresh_token: session.refresh_token,
    provider_token: session.provider_token,
    provider_refresh_token: session.provider_refresh_token,
  }),
})
// → { access_token, refresh_token, user, ... }  앱 JWT
```

### API

| Method | Path | 설명 |
|---|---|---|
| GET | `/auth/oauth/google` | authorize_url + state 쿠키 |
| GET | `/auth/oauth/google/redirect` | 브라우저 즉시 리다이렉트 |
| GET | `/auth/oauth/callback` | Supabase PKCE 콜백 |
| POST | `/auth/oauth/supabase` | Supabase AT → 앱 세션 교환 |
| POST | `/auth/refresh` | refresh 로테이션 |
| POST | `/auth/logout` | 세션 폐기 |
| GET | `/auth/me` | 현재 사용자 (`Authorization: Bearer`) |

## 구조

```
app/
  main.py              FastAPI 진입점·CORS·보안 헤더·라우터
  config.py            환경변수 (pydantic-settings)
  db.py                SQLAlchemy async 엔진·세션
  deps.py              인증 의존성
  security/            JWT·Fernet
  services/            Supabase Auth 클라이언트·유저 업서트
  schemas/             요청/응답 모델
  routers/
    health.py          /health, /db-ping
    auth.py            /auth/* OAuth·세션
db/
  migrations/          번호순 마이그레이션 SQL
  README.md
pyproject.toml
```

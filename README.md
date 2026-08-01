# PromButter Backend

FastAPI 기반 **DB 세팅·연결·SQL 전달용** 백엔드. PostgreSQL(Supabase) 사용.

> 이 레포는 **DB 스키마 셋업과 SQL 전달**이 목적이며, 서비스로 **배포하지 않는다.**
> 포함된 FastAPI 앱은 로컬에서 DB 연결을 확인(`/db-ping`)하고 인증/워크스페이스 API를 개발하기 위한 것이다.

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

## 구조

```
app/
  main.py        FastAPI 앱 진입점·CORS·라우터 등록
  config.py      환경변수 (pydantic-settings)
  db.py          SQLAlchemy async 엔진·세션
  routers/
    health.py    /health, /db-ping
db/
  migrations/    번호순 마이그레이션 SQL (0001_init.sql = 초기 전체 스키마)
  README.md      마이그레이션 관리 규칙
pyproject.toml   uv 의존성
```

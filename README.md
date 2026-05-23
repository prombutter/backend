# PromButter Backend

FastAPI 백엔드. PostgreSQL(Supabase) 사용, Cloud Run 배포 전제.

## 로컬 실행

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
5. Pooler(6543) 사용 권장 — 서버리스/Cloud Run 환경에서 안정적

## GCP Cloud Run 배포

### 사전 준비
- gcloud CLI 설치 및 `gcloud auth login`
- GCP 프로젝트 생성 후 `gcloud config set project <PROJECT_ID>`
- API 활성화: Cloud Run, Cloud Build, Artifact Registry

### 배포

```powershell
gcloud run deploy prombutter-backend `
  --source . `
  --region asia-northeast3 `
  --allow-unauthenticated `
  --set-env-vars APP_ENV=production `
  --set-env-vars CORS_ORIGINS=https://frontend-prombutters-projects.vercel.app `
  --set-secrets DATABASE_URL=DATABASE_URL:latest
```

`DATABASE_URL` 은 Secret Manager 에 먼저 등록:

```powershell
echo "postgresql+asyncpg://..." | gcloud secrets create DATABASE_URL --data-file=-
```

## 구조

```
app/
  main.py        FastAPI 앱 진입점·CORS·라우터 등록
  config.py      환경변수 (pydantic-settings)
  db.py          SQLAlchemy async 엔진·세션
  routers/
    health.py    /health, /db-ping
Dockerfile       Cloud Run 컨테이너
pyproject.toml   uv 의존성
```

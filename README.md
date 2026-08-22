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

## 파일 인코딩 규칙

이 레포의 모든 텍스트 파일은 **BOM 없는 UTF-8**, 줄바꿈은 **LF** 로 저장한다.

파이썬은 소스 파일을 UTF-8 로만 읽는다. `app/core/utils.py` 가 UTF-16 으로
저장된 적이 있었는데, `import` 하는 순간 아래 에러가 나면서 이 파일을 쓰는
`app/routers/prompts.py`, `app/routers/parts.py` 가 전부 죽었다.
테스트 18건이 한 번에 실패했고 CI 가 막히면서 배포도 함께 멈췄다.

```
SyntaxError: source code string cannot contain null bytes
```

커밋 전에 아래로 확인할 수 있다. CI 에서도 배포 전에 같은 검사를 하며,
실패하면 테스트가 멈추고 배포까지 진행되지 않는다.

```powershell
python scripts/check_encoding.py
```

### Windows 에서 자주 생기는 원인

- **메모장** 에서 "다른 이름으로 저장" 시 인코딩을 UTF-8 로 지정하지 않은 경우
- **PowerShell 5.1 의 `>` 리다이렉트** — 기본 저장 형식이 UTF-16 LE 다.
  파일을 만들 때는 `Out-File -Encoding utf8NoBOM` 을 쓰거나 에디터로 저장한다.
- VS Code 는 창 오른쪽 아래에 현재 인코딩이 표시된다. 그것을 눌러
  **Save with Encoding → UTF-8** 로 다시 저장할 수 있다.

이미 깨진 파일은 아래로 고친다.

```powershell
iconv -f UTF-16LE -t UTF-8 <파일> > tmp; mv tmp <파일>
```

`git diff` 나 `git pull` 결과에 소스 파일이 `Bin 0 -> 566 bytes` 처럼 표시되면
git 이 그 파일을 바이너리로 인식했다는 뜻이고, 인코딩이 깨졌다는 신호다.

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

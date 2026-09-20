# 배포 운영 (브랜치 · 파이프라인 · 롤백)

PB-140 에서 확정한 운영 배포 구조를 적는다. 스키마 규칙 자체는 [db/README.md](db/README.md) 가 진원이고,
여기는 "그 SQL 이 언제 어떤 DB 에 어떻게 올라가는가" 를 다룬다.

## 0. 확정 사항 (PB-140, 2026-09-21)

| 항목 | 확정 |
|---|---|
| 도메인 구성 | 커스텀 도메인 없이 현행 유지. FE `*.vercel.app` ↔ API `*.run.app` |
| 쿠키 | `SameSite=None` · `Secure=true` · `Domain` 미지정 |
| EXT 인증 | ① 쿠키 방식. 익스텐션 요청에도 같은 세션 쿠키를 동봉한다 |

FE 와 API 가 서로 다른 사이트라 `Lax` 로는 로그인 세션이 전송되지 않는다. 익스텐션은 `chatgpt.com`
컨텍스트에서 도니 어떤 도메인 구성을 골랐든 크로스 사이트다. 두 사정이 같은 답으로 모인다.

`SameSite=None` 은 웹 세션의 CSRF 노출면을 넓힌다. 다음 두 가지로 좁힌다.

- **CORS 허용 원점을 `chrome-extension://<확장ID>` 로 한정한다.** `chatgpt.com` 을 열지 않는다.
  페이지에 주입된 아무 스크립트나 사용자 세션으로 API 를 부를 수 있게 되기 때문이다.
  content script 는 직접 부르지 말고 service worker 를 거친다.
- **API 가 JSON 전용이라 preflight 가 걸린다.** 단순 요청으로 상태를 바꾸는 경로를 만들지 않는다.
  경로 하나라도 폼 인코딩을 받기 시작하면 이 방어가 사라진다.

확장 ID 는 manifest 에 `key` 를 박아 고정해야 한다. 고정하지 않으면 개발 설치와 웹스토어 배포의
ID 가 달라 CORS 허용 목록이 한쪽에서만 맞는다.

## 1. 브랜치

2 브랜치로 간다.

| 브랜치 | 역할 | 배포 대상 | 만드는 방법 |
|---|---|---|---|
| `dev` | 기본 작업 브랜치, 통합 | `prombutter-api-staging` | feature/bugfix 브랜치를 PR 로 Squash 머지 |
| `main` | 운영 | `prombutter-api-prod` | `dev` → `main` PR 머지 (릴리즈) |

`v*` 태그는 `main` 기준으로 붙이며 운영 배포를 한 번 더 태운다. 릴리즈 시점을 되짚기 위한 표식이고,
배포 경로 자체는 `main` 푸시와 같다.

핫픽스는 `main` 에서 잘라 `main` 으로 머지하고, 같은 커밋을 `dev` 에도 되돌려 머지한다.
`dev` 에 되돌리지 않으면 다음 릴리즈가 수정본을 덮는다.

## 2. 파이프라인

`.github/workflows/ci-cd.yml` 한 파일이다.

```
push (dev|main|v*) ─→ test ─→ deploy
                        │        ├ 1. DB 마이그레이션 적용   ← 실패하면 여기서 멈춘다
                        │        ├ 2. env.yaml 생성          ← 값 검증 실패 시 멈춘다
                        │        ├ 3. Cloud Run 배포
                        │        └ 4. 서비스 URL 기록 + /health 확인
                        └ 인코딩 검사 · 마이그레이션 2회 적용 · pytest
```

마이그레이션이 배포보다 **먼저** 돈다. 실패하면 새 리비전이 뜨지 않고 이전 리비전이 계속 트래픽을 받는다.
스키마가 없는 코드가 살아나 500 을 쏟는 것보다 낫다.

`test` 잡은 마이그레이션 러너를 같은 DB 에 두 번 돌린다. 운영에서 처음 재실행되는 일이 없도록,
재실행 안전성을 매 푸시마다 확인한다.

## 3. 마이그레이션 러너

`scripts/apply_migrations.sh` 가 `db/migrations/*.sql` 를 이름순으로 적용한다.

적용 기록은 대상 DB 의 `public.schema_migrations` 테이블에 남는다. 이미 기록된 파일은 건너뛴다.
파일이 멱등하게 쓰여 있어도 운영 DB 에 매번 전량을 다시 붓는 것은 다른 문제다.
되돌릴 수 없는 DDL 이 하나라도 섞이는 순간 그 방식은 사고가 된다.

```bash
# 미적용분 적용
scripts/apply_migrations.sh "$DATABASE_URL"

# 무엇이 적용될지만 확인
scripts/apply_migrations.sh "$DATABASE_URL" --dry-run

# 이미 스키마가 들어 있는 기존 DB 를 원장에 편입 (딱 한 번)
scripts/apply_migrations.sh "$DATABASE_URL" --baseline
```

`postgresql+asyncpg://` 스킴은 러너가 알아서 벗긴다. 앱과 같은 시크릿 하나를 그대로 쓰면 된다.

### 운영 DB 최초 편입

운영 DB 를 새로 만들었다면 그냥 적용한다. 이미 스키마가 올라가 있는 DB 라면 `--baseline` 으로
"적용된 것으로 기록" 만 하고 넘어간다. 이 구분을 틀리면 0001 이 이미 있는 테이블 위에 다시 돈다.

## 4. 환경변수

`scripts/build_env_yaml.py` 가 GitHub Secrets · Variables 를 읽어 `env.yaml` 을 만든다.

- 비밀값은 **Secrets** : `SECRET_KEY` · `DATABASE_URL` · `CORS_ORIGINS` · `GCP_CREDENTIALS` ·
  `SUPABASE_*` · `OAUTH_TOKEN_KEY` · `SENDGRID_API_KEY`
- 비밀이 아닌 설정은 **Variables** : `COOKIE_SECURE` · `COOKIE_SAMESITE` · `COOKIE_DOMAIN` ·
  `ACCESS_TOKEN_EXPIRE_MINUTES` · `REFRESH_TOKEN_EXPIRE_MINUTES` · `OAUTH_*` · `MAIL_FROM_ADDRESS`

Secrets 와 Variables 는 환경(`staging` · `production`)별로 따로 둔다. 같은 값을 쓰면 스테이징 배포가
운영 DB 에 마이그레이션을 건다.

빈 값은 키 자체를 주입하지 않는다. 빈 문자열을 넣으면 코드의 기본값이 덮여서
"미설정이라 기본값" 과 "빈 값으로 설정됨" 이 구분되지 않는다.

쿠키 조합은 주입 시점에 검증한다. `COOKIE_SAMESITE=none` 인데 `COOKIE_SECURE` 가 켜져 있지 않으면
배포가 멈춘다. 이 조합이 틀리면 브라우저가 쿠키를 조용히 버리고, 증상은 "로그인이 자꾸 풀린다" 하나뿐이다.

## 5. 롤백

raw SQL 로 스키마를 관리하므로 down 스크립트가 자동으로 생기지 않는다. 코드와 스키마를 따로 되돌린다.

### 5.1 코드만 되돌리기 (대부분의 경우)

스키마 변경이 없던 배포라면 Cloud Run 리비전만 되돌리면 끝이다. 가장 빠르고 안전하다.

```bash
gcloud run revisions list --service prombutter-api-prod --region asia-northeast3
gcloud run services update-traffic prombutter-api-prod \
  --region asia-northeast3 --to-revisions <직전_리비전>=100
```

되돌린 뒤 `git revert` 로 `main` 을 정리한다. 리비전만 되돌리고 코드를 두면 다음 배포가 같은 문제를 다시 올린다.

### 5.2 스키마까지 되돌려야 할 때

1. 먼저 5.1 로 트래픽을 이전 리비전에 넘긴다. 사용자 영향을 먼저 끊는다.
2. 되돌릴 마이그레이션의 역방향 SQL 을 손으로 쓴다. `db/migrations/` 에 새 번호로 **추가** 한다
   (`000N_revert_000M_<사유>.sql`). 이미 적용된 파일은 고치지 않는다.
3. 스테이징에 먼저 적용해 확인한다.
4. 운영에 적용한다.

원장에서 행을 지워 "안 적용된 것으로" 만드는 우회는 하지 않는다. DB 의 실제 상태와 기록이 어긋나고,
그 어긋남은 다음 배포 때 엉뚱한 파일이 돌면서 드러난다.

### 5.3 되돌릴 수 없는 변경

`DROP COLUMN` · `DROP TABLE` 처럼 데이터가 사라지는 변경은 롤백이 존재하지 않는다. 복구 수단은 백업뿐이다.
그런 마이그레이션은 두 단계로 나눈다. 먼저 쓰기를 끊고 한 배포를 흘려보낸 뒤, 다음 배포에서 지운다.

## 6. 자주 막히는 지점

| 증상 | 원인 |
|---|---|
| 로그인이 되는데 새로고침하면 풀린다 | FE 와 API 가 다른 사이트인데 `COOKIE_SAMESITE=lax` |
| 쿠키가 아예 안 실린다 | `SameSite=none` 인데 `Secure` 가 꺼져 있다. 브라우저가 버린다 |
| 로그아웃했는데 세션이 살아 있다 | 삭제할 때의 path·domain 이 심을 때와 다르다 |
| 배포는 성공인데 500 | 마이그레이션이 스테이징에만 적용됐다. 환경별 `DATABASE_URL` 확인 |

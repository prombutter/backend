# Prombutter 운영 배포

2026-10-03 운영자 결정: 프론트와 Python API는 Vercel에 배포하고 DB와 OAuth 인증은 Supabase를 사용한다. 확장은 현재 Chrome의 개발자 모드 설치본을 갱신한다.

## 구성

| 대상 | 운영 환경 |
|---|---|
| 프론트 | prombutter/frontend, Next.js, Vercel |
| Python API | prombutter/backend, FastAPI, 별도 Vercel 프로젝트 |
| DB·OAuth | Supabase 프로젝트 gkyzvjxycidxkhqrjvfu |
| 확장 | extension 폴더의 압축 해제 설치본 |

기존 Cloud Run 자동 배포 잡은 제거했다. GitHub Actions는 격리된 PostgreSQL에서 마이그레이션 초기화·재실행과 전체 테스트를 검증한다. CI는 운영 DB를 변경하지 않는다.

## 배포 전 검증

1. 프론트는 npm ci 후 lint, build, typecheck를 통과한다. build가 Next.js 타입 파일을 생성하므로 build와 typecheck를 동시에 실행하지 않는다.
2. 백엔드는 인코딩 검사와 전체 pytest를 통과한다. tests/conftest.py가 테스트 데이터를 쓰므로 운영 DATABASE_URL로 pytest를 실행하지 않는다.
3. 배포 대상 Vercel 팀과 두 프로젝트를 확인한다. 다른 프로젝트의 기본 CLI 설정을 재사용하지 않는다.
4. Supabase 운영 스키마와 db/migrations의 적용 상태를 확인한다. 확인되지 않은 마이그레이션을 실행하지 않는다.
5. 운영 인증, CORS, 쿠키 설정을 확인한 뒤 배포한다. 배포 후 health와 DB 연결, 정상·실패 인증 경로 및 저장된 운영 로그를 확인한다.
6. 실제 API 전용 DB 계정으로 `scripts/check_runtime_sequence_permissions.sql`을 실행한다. 모든 행의 `insert_allowed`와 `nextval_allowed`가 참이어야 한다. 테이블 권한과 DB 연결만으로 INSERT 가능 여부를 판단하지 않는다. 소유 관계 없이 `DEFAULT nextval(...)`로 연결한 시퀀스도 검사한다.

이메일 로그인은 성공·실패 모두 `login_attempts`에 기록한다. API 계정에는 해당 테이블의 INSERT 권한과 `login_attempts_id_seq`의 USAGE 권한이 함께 필요하다. 누락 시 로그인 요청이 500 오류로 실패한다. 운영 보완은 확인된 API 계정과 해당 시퀀스로 한정하며, 익명·인증 사용자 권한과 시퀀스 값은 변경하지 않는다.

## Vercel Python API

pyproject.toml의 project.scripts.app은 app.main:app을 가리킨다. Vercel의 FastAPI 감지가 이 진입점을 사용한다. Cloud Run용 Dockerfile은 Vercel 진입점이 아니다.

.vercelignore는 로컬 시크릿, 인증 설정, 개발 환경, 로그, 내부 문서와 확장 리소스를 업로드에서 제외한다. Vercel 프로젝트 연결 정보인 .vercel 폴더는 Git에 추가하지 않는다.

운영 프로젝트의 환경변수에 다음 키를 등록한다. 비밀값은 중앙 Secrets에서 대상 서비스로 전달하고 대화·로그·문서에 출력하지 않는다.

| 종류 | 키 |
|---|---|
| 필수 비밀값 | SECRET_KEY, DATABASE_URL |
| OAuth 비밀값 | SUPABASE_URL, SUPABASE_ANON_KEY, 필요한 경우 SUPABASE_SERVICE_ROLE_KEY, OAUTH_TOKEN_KEY |
| 운영 설정 | APP_ENV=production, COOKIE_SECURE=true, COOKIE_SAMESITE=none |
| 접근 설정 | CORS_ORIGINS, OAUTH_CALLBACK_URL, OAUTH_FRONTEND_REDIRECT, OAUTH_ALLOWED_REDIRECTS |
| 이메일 사용 시 | SENDGRID_API_KEY, MAIL_FROM_ADDRESS |

DATABASE_URL은 앱이 사용하는 postgresql+asyncpg 스킴과 대상 Supabase 연결 방식을 맞춘다. CORS_ORIGINS에는 실제 프론트 오리진과 현재 확장의 chrome-extension 오리진을 명시한다. 와일드카드는 사용하지 않는다.

운영 API URL은 Vercel 배포 성공 후 확정한다. 해당 URL을 프론트의 API 프록시와 확장의 API_BASE 및 host_permissions에 함께 반영한다.

## Supabase 마이그레이션

0001_init.sql은 기존 테이블을 DROP TABLE CASCADE로 삭제한다. 데이터가 있는 DB에 직접 실행하지 않는다.

scripts/apply_migrations.sh는 적용 원장을 확인한다. 원장이 비어 있는데 앱 테이블이 있으면 적용을 거부한다. 기존 운영 DB는 스키마 대조 후 이미 적용된 마이그레이션만 baseline으로 기록한다. baseline도 DB 변경이므로 사전 대조와 독립 검토를 마친 뒤 수행한다.

## OAuth 콜백

Google Cloud OAuth 클라이언트의 승인된 리디렉션 URI에는 아래 Supabase 주소를 등록한다.

https://gkyzvjxycidxkhqrjvfu.supabase.co/auth/v1/callback

이 주소와 앱의 OAUTH_CALLBACK_URL은 서로 다른 단계다. OAUTH_CALLBACK_URL은 실제 Python API의 /auth/oauth/callback을 가리키고, OAUTH_FRONTEND_REDIRECT는 실제 프론트의 인증 완료 화면을 가리킨다. Supabase URL 허용 목록도 이 흐름에 맞춘다.

운영 프론트는 이메일 로그인·회원가입 후 인증 쿠키를 확인하고, 현재 계정의 workspace ID를 API에서 조회한다. Google 로그인은 Python API의 OAuth 시작 경로에 연결한다. 프론트 NEXT_PUBLIC_API_BASE_URL에는 실제 운영 API 오리진을 등록한다. 운영 빌드는 이 HTTPS 설정이 없으면 중단한다. 빌드 성공만으로 실제 브라우저의 로그인이나 데이터 연동이 완료되었다고 판단하지 않는다.

## 확장 갱신

운영 API와 프론트 주소가 확정되면 src/shared/config.js의 API_BASE와 WEBAPP_BASE, 콘텐츠 스크립트의 웹앱 주소, manifest의 host_permissions와 설치 표식 matches를 함께 맞춘다.

JavaScript 구문, manifest 리소스, 전 로케일 키 누락을 검사한다. 그 후 Chrome의 현재 설치 폴더와 확장 ID를 확인하고 기존 설치본을 새로고침한다. 서비스 워커의 실제 요청, 쿠키 전송, 갱신 성공과 로그인 필요 상태를 확인한다.

이 작업은 개발자 모드 설치본 갱신이다. Chrome Web Store 게시를 수행하지 않는다.

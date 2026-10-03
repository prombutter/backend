# Prombutter Chrome Extension

Prombutter 프롬프트 관리 서비스의 크롬 확장 프로그램 (Manifest V3).

ChatGPT·Claude 입력창 위에 즐겨찾기 프롬프트를 띄우고 원클릭으로 주입한다 (기획서 4.2 EXT-WIDGET).

## 전제

일반 기능은 현재 백엔드 API를 그대로 소비한다. 로컬 개발자 로그인은
개발 환경 전용 `POST /auth/developer-login`을 사용한다.
API 가 없어서 못 하는 기능은 확장 쪽에서 우회하거나 범위 밖으로 남기고, 백엔드 변경을
전제한 구현은 두지 않는다.

## 폴더 구조

| 경로 | 용도 |
|---|---|
| `manifest.json` | MV3 매니페스트 |
| `src/background/service-worker.js` | 백엔드 호출·인증 갱신·메시지 라우팅 |
| `src/content/widget.js` | EXT-WIDGET (Entry + Panel), 입력창 주입 |
| `src/content/install-flag.js` | 웹 앱에 설치 표식 주입 (기획서 4.3.1) |
| `src/shared/` | 서비스 워커·팝업이 쓰는 공용 모듈 (설정·API 래퍼) |
| `src/popup/`, `src/options/` | 툴바 팝업·옵션 화면 |
| `styles/widget.css` | 위젯 스타일 (Shadow DOM 안에서만 적용) |
| `_locales/ko`, `_locales/en` | 사용자 노출 문구. 하드코딩 금지 |

## 사용하는 백엔드 API

일반 인증과 즐겨찾기에는 기존 엔드포인트를 사용한다.

| 메서드 · 경로 | 쓰임 |
|---|---|
| `GET /workspaces` | 현재 로그인 계정의 워크스페이스 ID |
| `GET /workspaces/{ws}/prompts/favorites` | 즐겨찾기 목록 (최대 5개 노출) |
| `POST /workspaces/{ws}/prompts/{id}/render` | 완성 프롬프트 렌더. `missing` 이 있으면 변수 있는 프롬프트로 판정 |
| `POST /auth/refresh` | 401 응답 시 1회 자동 갱신 |
| `POST /auth/developer-login` | 로컬 개발 계정의 AT/RT 쿠키 발급 |
| `GET /auth/me` | 개발자 로그인 뒤 쿠키 인증 확인 |

변수 유무 판정에 `GET /prompts/{id}/variables` 대신 `render` 의 `missing` 을 쓰는 이유는
호출을 한 번으로 줄이기 위해서다. 변수가 없으면 그 응답의 `rendered` 를 그대로 주입한다.

## 인증

백엔드는 HttpOnly 쿠키(`access_token` / `refresh_token`, SameSite=Lax)로 인증한다.
그래서 확장도 토큰을 따로 보관하지 않고 쿠키를 그대로 쓴다.

- 모든 요청은 서비스 워커에서 `credentials: 'include'` 로 나간다.
- 크롬은 확장이 `host_permissions` 를 가진 오리진으로 보내는 요청을 same-site 로 취급하므로
  SameSite=Lax 쿠키가 함께 실린다. 따라서 백엔드 쿠키 설정을 바꿀 필요가 없다.
- 401 이면 `refresh` 를 한 번 시도하고 재요청한다. 그래도 실패하면 위젯이 '로그인 필요'
  상태로 내려가고, 로그인은 웹 앱에서 한다.

> 실기기 확인 항목: 쿠키가 실제로 실리는지는 브라우저에서 한 번 확인해야 한다.
> 만약 실리지 않으면 `cookies` + `declarativeNetRequest` 권한으로 Cookie 헤더를 직접
> 붙이는 우회가 있다. 어느 쪽이든 백엔드 변경은 필요 없다.

### 개발자 로그인

로컬 API를 사용하는 위젯에서는 로그인 버튼 옆에 「개발자 로그인」이 나타난다.
백엔드를 `APP_ENV=local`과 `DEVELOPER_LOGIN_ENABLED=true`로 실행한 뒤 이 버튼을 누르면,
이메일·비밀번호 입력 없이 전용 개발 계정으로 인증한다. 계정과 워크스페이스는 최초에
한 번 만들고 이후 재사용한다. 기존 계정의 데이터는 개발 계정으로 옮기지 않는다.

서버 실행 프로세스에 두 환경변수를 설정한다. 기본 설정에서는 개발자 로그인이 꺼져 있다.
운영용 확장의 기본 주소는 Vercel이다. 로컬 개발 시에는 `src/shared/config.js`의
`API_BASE`를 `http://localhost:8000`, `WEBAPP_BASE`를 `http://localhost:3000`으로 함께 바꾼다.
운영 API를 사용하는 확장에서는 개발자 로그인 버튼을 표시하지 않는다.

```powershell
$env:APP_ENV = 'local'
$env:DEVELOPER_LOGIN_ENABLED = 'true'
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

운영·스테이징, 외부 호스트·클라이언트, 프록시 헤더, 일반 웹 페이지의 호출은 거부한다.
백엔드는 확장의 `X-Requested-With` 헤더를 확인하고, Origin이 있으면 확장 출처만 허용한다.
익스텐션은 인증 뒤 `/auth/me`로 쿠키를 확인하고 즐겨찾기를 다시 불러온다.

결과 이벤트 `developer_login_result`는 기존 `chrome.storage.local.eventBuffer`에 저장한다.
UTC 시각, 요청 ID, 성공·실패·차단 분류, 원인 코드와 소요 시간만 기록한다.
이 이벤트에는 인증 토큰, 이메일, 비밀번호, 프롬프트 본문을 넣지 않는다.
브라우저 저장소에 기록하지 못하면 서비스 워커에 `storage_failed`와 요청 ID를 남긴다.
로그 저장 실패가 완료된 인증 결과를 바꾸지는 않는다.
운영 주소 접근 권한이 없는 설치본은 즐겨찾기 요청 전에 `ERR-EXT-010`으로 안내한다.
이때 `extension_api_access_result` 이벤트에 `blocked`와 `HOST_PERMISSION_MISSING`을 저장한다.

코드 변경 후 `chrome://extensions`에서 익스텐션을 새로고침하고 사용 중인 LLM 페이지도
새로고침한다. 처음 생성된 개발 계정에는 즐겨찾기가 없으므로 웹 앱에서 등록한다.

## 로컬 실행

1. 백엔드를 `http://localhost:8000` 에 띄운다.
2. 웹 앱을 `http://localhost:3000` 에 띄우고 로그인한다 (쿠키가 심어져야 한다).
3. `chrome://extensions` → 개발자 모드 → 「압축해제된 확장 프로그램을 로드」 → 이 폴더 선택.
4. ChatGPT 또는 Claude 를 열면 입력창 위에 Entry 가, 화면 우하단에 패널 앵커가 붙는다.

주소를 바꾸려면 `src/shared/config.js` 의 `API_BASE`·`WEBAPP_BASE` 와
`manifest.json` 의 `host_permissions`·`content_scripts.matches` 를 함께 고친다.

## 확인이 필요한 것

- **웹 앱 화면 경로** — `src/content/widget.js` 의 `ROUTES` 는 추정값이다.
  프론트엔드 라우팅과 대조해야 한다.
- **운영 쿠키 전송**: 실제 설치된 Chrome 확장에서 쿠키 전송과 갱신을 확인한다.
- **아이콘** — `assets/icons/*` 는 단색 자리표시자다.

## 범위 밖

- **이벤트 수집** — 백엔드에 수집 엔드포인트가 없다. 유실을 막으려고 주입·새 탭 이벤트를
  `storage.local` 에 200건 상한으로 쌓아두기만 한다. 보낼 곳이 생기기 전까지는 로컬에만 남는다.
- **위젯 내 변수 입력** — MVP 규칙상 금지 (기획서 4.2.3). 변수가 있는 프롬프트는 웹 앱 새 탭으로 넘긴다.

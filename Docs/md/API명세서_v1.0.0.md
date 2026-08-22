# PromButter API 명세서

본 문서는 백엔드 팀이 작업한 API 엔드포인트의 규격을 정의한다. 프론트엔드 연동 및 기획 검토를 위한 기준으로 활용된다.

## 1. 파츠(Parts) 도메인 실 API 명세 (P3-W5)

실제 데이터베이스(Supabase)와 연동되며, 변수 추출 및 태그 정규화 코어 로직이 적용된 API 명세이다.

| Endpoint | Method | 목적 및 시스템 동작 | Request (Body / Param) | Response |
|---|---|---|---|---|
| `/api/v1/parts` | GET | 사용자가 속한 워크스페이스의 파츠 목록을 조회한다. 텍스트 검색(`q`)을 지원하며, 휴지통(Soft Delete)으로 이동한 파츠는 제외하고 반환한다. | `Query: q (Optional, String)` | `List[PartResponse]` |
| `/api/v1/parts/{id}` | GET | 특정 파츠의 상세 정보를 조회한다. 파츠에 연결된 태그 목록을 함께 반환한다. | `Path: id (UUID)` | `PartResponse` |
| `/api/v1/parts` | POST | 신규 파츠를 생성한다. 본문 내 `{{변수}}`를 자동 추출하여 저장하며, 태그(최대 10개)는 소문자로 정규화하여 저장한다. | `Body: PartCreate (title, body, tags)` | `PartResponse` |
| `/api/v1/parts/{id}` | PUT | 파츠 정보를 수정한다. 본문(`body`)이 수정될 경우 변수 목록도 재추출하여 갱신한다. 즐겨찾기(`is_favorite`) 상태 변경도 이 엔드포인트를 통해 처리한다. | `Body: PartUpdate (선택적 필드)` | `PartResponse` |
| `/api/v1/parts/{id}` | DELETE | 파츠를 휴지통으로 이동한다 (Soft Delete). 실제 DB 레코드를 파기하지 않고 `deleted_at` 타임스탬프를 설정한다. | `Path: id (UUID)` | `{"success": true}` |
| `/api/v1/parts/{id}/duplicate` | POST | 기존 파츠를 복제하여 새로운 파츠를 생성한다. 제목 끝에 `(Copy)`가 자동으로 추가되며 기존 변수와 태그도 복제된다. | `Path: id (UUID)` | `PartResponse` |

단, `POST`, `PUT` 시 `title`은 최대 100자, `body`는 최대 700자로 제한한다.

---

## 2. 기타 도메인 Mock API 명세 (P1)

프론트엔드 개발 언블로킹을 위해 임시로 제공되는 가짜(Mock) 데이터 반환 엔드포인트이다.

| Endpoint | Method | 목적 및 시스템 동작 | Request (Body / Param) | Response |
|---|---|---|---|---|
| `/api/v1/auth/login` | POST | 테스트용 더미 액세스 토큰과 유저 정보를 반환한다. | `Body: email, password` | `{token, user}` |
| `/api/v1/auth/register` | POST | 회원가입 성공 더미 응답을 반환한다. | `Body: email, password, name` | `{token, user}` |
| `/api/v1/prompts` | GET/POST | 더미 프롬프트 조합 목록 조회 및 생성 응답을 반환한다. | - | `List[Prompt]` / `Prompt` |
| `/api/v1/gallery/templates` | GET | 갤러리 내 샘플 템플릿 목록 더미 데이터를 반환한다. | - | `List[Template]` |
| `/api/v1/dashboard/stats` | GET | 워크스페이스 대시보드용 더미 통계 지표(사용량 등)를 반환한다. | - | `{stats...}` |

※ 향후 인증 및 프롬프트 로직 등 동료 개발자의 API 실구현이 완료되면 본 명세서 하단에 섹션을 추가하여 통합한다.

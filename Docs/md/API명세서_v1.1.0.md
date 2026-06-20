# API 명세서 v1.1.0

본 문서는 promButter 백엔드 시스템의 주요 도메인 API 명세를 정의한다.

## 1. 파츠(Parts) 도메인

파츠 관리에 대한 전반적인 CRUD, 휴지통(Soft Delete), 복원, 즐겨찾기 기능을 관리한다.

주요 접근 대상: User.
연관 시스템: 없음.
핵심 테이블: parts, tags, entity_tags.

### 1.1. 단일 파츠 생성 (P1)

| 항목 | 내용 |
|---|---|
| **URI** | `POST /api/v1/workspaces/{workspace_id}/parts` |
| **설명** | 워크스페이스 내 신규 파츠를 생성한다. |
| **Request Body** | - `title`: 파츠 제목 (최대 100자)<br>- `body`: 파츠 본문 (최대 700자)<br>- `tags`: 태그 배열 (각 최대 30자) |
| **Validation** | 글자 수 제한 초과 시 422 Unprocessable Entity 반환 |
| **Server 동작** | 파츠 본문 내 `{{...}}` 패턴을 분석하여 `variable_count`를 동적 계산 후 반환한다. |
| **DB 처리 방식** | `parts` 테이블 INSERT, 입력된 태그는 `tags` 테이블 및 `entity_tags` 다대다 연결 처리한다. |

### 1.2. 파츠 목록 및 휴지통 조회 (P3-W5)

| 항목 | 내용 |
|---|---|
| **URI** | `GET /api/v1/workspaces/{workspace_id}/parts` |
| **Query Param** | `is_deleted` (Boolean, 선택, 기본값 false) |
| **설명** | 조건에 맞는 파츠 목록을 조회한다. |
| **Server 동작** | `is_deleted=true` 인 경우 휴지통(deleted_at is not null) 목록을 반환하며, `false` 인 경우 일반 목록(deleted_at is null)을 반환한다. |
| **DB 처리 방식** | `parts` 테이블 SELECT (최신순 정렬). |

### 1.3. 단일 파츠 조회

| 항목 | 내용 |
|---|---|
| **URI** | `GET /api/v1/workspaces/{workspace_id}/parts/{id}` |
| **설명** | ID에 해당하는 단일 파츠 상세 정보를 조회한다. |
| **Server 동작** | 파츠 데이터가 존재하지 않거나 삭제된 경우 404 Not Found 반환한다. |

### 1.4. 파츠 수정 (P1)

| 항목 | 내용 |
|---|---|
| **URI** | `PATCH /api/v1/workspaces/{workspace_id}/parts/{id}` |
| **설명** | 파츠의 일부 필드를 수정한다. |
| **Request Body** | - `title`: (선택)<br>- `body`: (선택)<br>- `is_favorite`: (선택)<br>- `tags`: (선택, 배열) |
| **Server 동작** | 입력된 필드만 추출하여 갱신한다. 본문 변경 시 `variable_count`를 재계산하여 반환한다. `tags`가 제공된 경우 기존 태그 관계를 삭제하고 새로 연결한다. |
| **DB 처리 방식** | `parts` 테이블 UPDATE. |

### 1.5. 파츠 복제

| 항목 | 내용 |
|---|---|
| **URI** | `POST /api/v1/workspaces/{workspace_id}/parts/{id}/duplicate` |
| **설명** | 기존 파츠를 기반으로 복제본을 생성한다. |
| **Server 동작** | 원본 파츠의 제목 뒤에 `(복사본)` 텍스트를 덧붙여 신규 레코드로 저장한다. |

### 1.6. 파츠 휴지통 이동 / Soft Delete (P3-W5)

| 항목 | 내용 |
|---|---|
| **URI** | `DELETE /api/v1/workspaces/{workspace_id}/parts/{id}` |
| **설명** | 지정된 파츠를 휴지통으로 이동시킨다. |
| **DB 처리 방식** | 대상 레코드의 `deleted_at` 컬럼에 현재 시간을 UPDATE (논리 삭제) 처리한다. |

### 1.7. 파츠 영구 삭제 (P3-W5)

| 항목 | 내용 |
|---|---|
| **URI** | `DELETE /api/v1/workspaces/{workspace_id}/parts/{id}/permanent` |
| **설명** | 데이터베이스에서 파츠를 완전히 삭제한다. |
| **Server 동작** | 연관된 모든 데이터를 삭제하여 공간을 확보한다. |
| **DB 처리 방식** | `parts`, `entity_tags`, `variables` 등 연관된 레코드 연쇄 하드 삭제(DELETE) 처리한다. |

### 1.8. 파츠 복원 (P3-W5)

| 항목 | 내용 |
|---|---|
| **URI** | `POST /api/v1/workspaces/{workspace_id}/parts/{id}/restore` |
| **설명** | 휴지통에 위치한 파츠를 일반 목록으로 되돌린다. |
| **DB 처리 방식** | 대상 레코드의 `deleted_at` 컬럼을 `null` 로 UPDATE 처리한다. |

### 1.9. 파츠 즐겨찾기 토글 (P3-W5)

| 항목 | 내용 |
|---|---|
| **URI** | `POST /api/v1/workspaces/{workspace_id}/parts/{id}/favorite` |
| **설명** | 해당 파츠의 즐겨찾기(별표) 상태를 반전시킨다. |
| **Server 동작** | 기존 `is_favorite` 값을 반전시킨 뒤 갱신한다. |
| **DB 처리 방식** | `parts` 테이블의 `is_favorite` 컬럼 UPDATE. |

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

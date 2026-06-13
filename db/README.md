# DB 스키마 / 마이그레이션 규칙

이 레포는 PromButter 의 **DB 스키마 셋업과 SQL 전달**을 담당한다. 런타임 서비스로 배포하지 않으며,
스키마의 단일 출처(SSOT)는 이 `db/migrations/` 폴더의 번호순 SQL 파일이다.

## 폴더 구조

- `db/migrations/NNNN_<설명>.sql` — 번호순(0001, 0002, …) 누적 마이그레이션. 빈 DB 에 0001 부터 순서대로 실행하면 최신 스키마가 된다.
- `0001_init.sql` — 초기 전체 스키마. 확장(`citext`·`pgcrypto`) + enum 10종 + 전체 테이블/인덱스/FK 포함. **빈 DB 에 단독 실행 가능.**

## 빈 DB 최초 설치

```bash
psql "<DATABASE_URL>" -f db/migrations/0001_init.sql
```

(Supabase 는 Dashboard → SQL Editor 에 파일 내용을 붙여넣어 실행해도 된다.)

## 앞으로의 스키마 변경 규칙 (팀 규칙)

1. **도구 — Alembic 미사용, 번호순 raw SQL 로 관리한다.**
   이 레포에는 ORM 모델이 없고(스키마는 DA 툴에서 손으로 작성), 서비스로 배포하지도 않으므로
   Alembic 의 autogenerate 이점이 없다. 대신 번호순 SQL 파일로 관리한다.
   이 구조는 **Supabase CLI 의 `supabase/migrations/` 규칙과 호환**되므로, 추후 Supabase CLI 도입 시 그대로 이전 가능하다.
2. **추가 방법** — 변경이 생기면 새 파일 `db/migrations/000N_<설명>.sql` 을 추가한다.
   이미 적용·전달된 파일은 **수정하지 않는다** (적용된 DB 와의 정합 유지).
3. **멱등성 권장** — 가능한 한 `IF NOT EXISTS` / `IF EXISTS` / `DO $$ … duplicate_object … $$` 패턴으로
   재실행에 안전하게 작성한다 (`0001_init.sql` 의 prelude 참고).
4. **인코딩** — 마이그레이션 SQL 은 **UTF-8 (BOM 없음)** 으로 저장한다 (psql·Supabase 호환).
5. **검수** — `0001_init.sql` 의 enum 값은 컬럼 코멘트에서 역추출된 것이다(파일 머리말 경고 참조).
   신규 enum·값 추가 시 실제 도메인 값과 대조한다.

## 참고 — 루트의 DA 툴 산출물

`PromButter.damx`(DA 모델링 원본), `PromButter.sql`(DA 툴 diff 덤프 — 빈 DB 단독 실행 불가),
`PromButter.fixed.sql`(diff 덤프에 확장·enum prelude 를 보강한 버전) 은 모두 DA 툴 작업 파일이며
git 추적 대상이 아니다(로컬 보관). 전달·설치용 SSOT 는 `db/migrations/0001_init.sql` 이다.

-- ============================================================
-- 0002_add_unique_constraints.sql
-- 0001_init 에서 누락된 비-PK UNIQUE 제약 추가.
-- 원본 DA 툴 덤프가 비-PK unique 인덱스를 통째로 누락 → 모델 의도와 DDL 불일치를 정정한다.
-- 멱등: 이미 있으면 무시(DO/EXCEPTION). 0001 은 수정하지 않는다.
-- ※ 데이터가 이미 들어간 DB라면 적용 전 중복 정리 필요 (빈 DB면 무관).
-- ============================================================

-- [질문] workspaces.owner_id : 1인 1워크스페이스(D9). 컬럼 코멘트 '소유자 사용자 ID(1:1)' 와 정합
DO $$ BEGIN
    ALTER TABLE public.workspaces
        ADD CONSTRAINT uq_workspaces_owner UNIQUE (owner_id);
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- [질문] tokens.token_hash : 토큰은 해시로 조회 → 유일해야 함
DO $$ BEGIN
    ALTER TABLE public.tokens
        ADD CONSTRAINT uq_tokens_token_hash UNIQUE (token_hash);
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- [질문] user_sessions.refresh_token_hash : 세션 조회 키 → 유일해야 함
DO $$ BEGIN
    ALTER TABLE public.user_sessions
        ADD CONSTRAINT uq_user_sessions_refresh_token_hash UNIQUE (refresh_token_hash);
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- [추가발견] users.email : 이메일 로그인 식별자 (CITEXT → 대소문자 무시 유일)
DO $$ BEGIN
    ALTER TABLE public.users
        ADD CONSTRAINT uq_users_email UNIQUE (email);
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- [추가발견] user_identities (provider, provider_user_id) : 동일 외부 계정 중복 연결 방지
DO $$ BEGIN
    ALTER TABLE public.user_identities
        ADD CONSTRAINT uq_user_identities_provider_account UNIQUE (provider, provider_user_id);
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- [추가발견·검토권장] tags (workspace_id, name) : 워크스페이스 내 태그명 중복 방지
-- (제품 규칙상 동명 태그를 허용한다면 이 블록만 제거)
DO $$ BEGIN
    ALTER TABLE public.tags
        ADD CONSTRAINT uq_tags_workspace_name UNIQUE (workspace_id, name);
EXCEPTION WHEN duplicate_object THEN null; END $$;

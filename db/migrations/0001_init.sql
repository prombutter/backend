-- ============================================================
-- Auto-generated prelude: extensions + enum types
-- (extracted from column comments; verify values before prod)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN
    CREATE TYPE TAG_ENTITY_TYPE AS ENUM ('PROMPT', 'PART');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE VARIABLE_ENTITY_TYPE AS ENUM ('PROMPT', 'PART');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE REVISION_ENTITY_TYPE AS ENUM ('PROMPT', 'PART', 'TAG');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE EVENT_TARGET_TYPE AS ENUM ('PROMPT', 'PART', 'TAG');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE DEVICE_TYPE AS ENUM ('WEB', 'EXTENSION');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE ENTRY_POINT AS ENUM ('WEBAPP', 'EXT_ENTRY', 'EXT_PANEL');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE BLOCK_TYPE AS ENUM ('PART', 'INLINE');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE TOKEN_TYPE AS ENUM ('EMAIL_VERIFICATION', 'PASSWORD_RESET');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE AUTH_PROVIDER AS ENUM ('EMAIL', 'GOOGLE');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE USER_ROLE AS ENUM ('USER', 'SUPER_ADMIN');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- ============================================================
-- Original schema below
-- ============================================================

-- ============================================================
-- Sequences
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS login_attempts_id_seq;
DROP TABLE IF EXISTS public.entity_tags CASCADE;

CREATE TABLE public.entity_tags
(
    entity_type    TAG_ENTITY_TYPE NOT NULL,
    entity_id    UUID NOT NULL,
    tag_id    UUID NOT NULL
);

COMMENT ON COLUMN public.entity_tags.entity_type IS '대상 엔티티 종류';

COMMENT ON COLUMN public.entity_tags.entity_id IS '대상 엔티티 ID';

COMMENT ON COLUMN public.entity_tags.tag_id IS '태그 ID';

COMMENT ON TABLE public.entity_tags IS '엔티티-태그 연결';

CREATE UNIQUE INDEX pk_entity_tags ON public.entity_tags
( entity_type,entity_id,tag_id );

ALTER TABLE public.entity_tags
 ADD CONSTRAINT pk_entity_tags PRIMARY KEY 
 USING INDEX pk_entity_tags;


DROP TABLE IF EXISTS public.events CASCADE;

CREATE TABLE public.events
(
    id    bigint NOT NULL,
    event_name    character varying(80) NOT NULL,
    user_id    UUID,
    workspace_id    UUID,
    session_id    character varying(100),
    device_type    DEVICE_TYPE,
    prompt_has_vars    boolean,
    prompt_length    integer,
    error_code    character varying(80),
    error_message    text,
    properties    jsonb DEFAULT '{}'::jsonb NOT NULL,
    occurred_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    entry_point    ENTRY_POINT,
    target_entity_type    EVENT_TARGET_TYPE,
    target_entity_id    UUID
);

COMMENT ON COLUMN public.events.id IS '이벤트 ID';

COMMENT ON COLUMN public.events.event_name IS '이벤트명(예: prompt_inject_attempt)';

COMMENT ON COLUMN public.events.user_id IS '사용자 ID';

COMMENT ON COLUMN public.events.workspace_id IS '워크스페이스 ID';

COMMENT ON COLUMN public.events.session_id IS '세션 ID';

COMMENT ON COLUMN public.events.device_type IS '디바이스 유형(WEB/EXTENSION)';

COMMENT ON COLUMN public.events.prompt_has_vars IS '변수 포함 여부';

COMMENT ON COLUMN public.events.prompt_length IS '주입/복사된 텍스트 길이';

COMMENT ON COLUMN public.events.error_code IS '실패 코드';

COMMENT ON COLUMN public.events.error_message IS '실패 안내 메시지';

COMMENT ON COLUMN public.events.properties IS '추가 파라미터(JSONB)';

COMMENT ON COLUMN public.events.occurred_at IS '발생 시각';

COMMENT ON COLUMN public.events.entry_point IS '진입점 (WEBAPP/EXT_ENTRY/EXT_PANEL)';

COMMENT ON COLUMN public.events.target_entity_type IS '대상 엔티티 종류 (PROMPT/PART/TAG, 없으면 NULL)';

COMMENT ON COLUMN public.events.target_entity_id IS '대상 엔티티 ID (FK 미연결, 삭제 후에도 로그 보존)';

COMMENT ON TABLE public.events IS '이벤트 로그';

CREATE UNIQUE INDEX pk_events ON public.events
( id,occurred_at );

ALTER TABLE public.events
 ADD CONSTRAINT pk_events PRIMARY KEY 
 USING INDEX pk_events;


DROP TABLE IF EXISTS public.login_attempts CASCADE;

CREATE TABLE public.login_attempts
(
    id    bigint DEFAULT nextval('login_attempts_id_seq') NOT NULL,
    ip_address    INET,
    success    boolean NOT NULL,
    attempted_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    email_hash    character varying(64) NOT NULL
);

COMMENT ON COLUMN public.login_attempts.id IS '시도 ID';

COMMENT ON COLUMN public.login_attempts.ip_address IS 'IP 주소';

COMMENT ON COLUMN public.login_attempts.success IS '성공 여부';

COMMENT ON COLUMN public.login_attempts.attempted_at IS '시도 시각';

COMMENT ON COLUMN public.login_attempts.email_hash IS '이메일 해시 (소문자/trim 후 SHA-256 hex). 원본 이메일은 저장하지 않음(G';

COMMENT ON TABLE public.login_attempts IS '로그인 시도 기록(CAPTCHA 트리거 판단용)';

CREATE UNIQUE INDEX pk_login_attempts ON public.login_attempts
( id );

ALTER TABLE public.login_attempts
 ADD CONSTRAINT pk_login_attempts PRIMARY KEY 
 USING INDEX pk_login_attempts;


DROP TABLE IF EXISTS public.parts CASCADE;

CREATE TABLE public.parts
(
    id    UUID DEFAULT gen_random_uuid() NOT NULL,
    workspace_id    UUID NOT NULL,
    title    character varying(100) NOT NULL,
    body    character varying(700) NOT NULL,
    is_favorite    boolean DEFAULT 'false' NOT NULL,
    deleted_at    timestamp with time zone,
    purge_at    timestamp with time zone,
    created_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

COMMENT ON COLUMN public.parts.id IS '파츠 ID';

COMMENT ON COLUMN public.parts.workspace_id IS '워크스페이스 ID';

COMMENT ON COLUMN public.parts.title IS '제목(100자, 워크스페이스 내 중복 불가)';

COMMENT ON COLUMN public.parts.body IS '본문(700자)';

COMMENT ON COLUMN public.parts.is_favorite IS '파츠 즐겨찾기(, 편집 접근용)';

COMMENT ON COLUMN public.parts.deleted_at IS 'Soft Delete 시각';

COMMENT ON COLUMN public.parts.purge_at IS '영구 삭제 예정 시각(deleted_at + 30일)';

COMMENT ON COLUMN public.parts.created_at IS '생성 시각';

COMMENT ON COLUMN public.parts.updated_at IS '수정 시각';

COMMENT ON TABLE public.parts IS '파츠(프롬프트 재료)';

CREATE UNIQUE INDEX pk_parts ON public.parts
( id );

ALTER TABLE public.parts
 ADD CONSTRAINT pk_parts PRIMARY KEY 
 USING INDEX pk_parts;


DROP TABLE IF EXISTS public.prompt_blocks CASCADE;

CREATE TABLE public.prompt_blocks
(
    id    UUID DEFAULT gen_random_uuid() NOT NULL,
    prompt_id    UUID NOT NULL,
    part_id    UUID,
    inline_body    character varying(700),
    created_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    sort_order    integer NOT NULL,
    block_type    BLOCK_TYPE NOT NULL
);

COMMENT ON COLUMN public.prompt_blocks.id IS '블록 ID';

COMMENT ON COLUMN public.prompt_blocks.prompt_id IS '프롬프트 ID';

COMMENT ON COLUMN public.prompt_blocks.part_id IS '파츠 ID(kind=PART)';

COMMENT ON COLUMN public.prompt_blocks.inline_body IS '인라인 본문(kind=INLINE, 700자)';

COMMENT ON COLUMN public.prompt_blocks.created_at IS '생성 시각';

COMMENT ON COLUMN public.prompt_blocks.sort_order IS '정렬 순서';

COMMENT ON COLUMN public.prompt_blocks.block_type IS '블록 종류 (PART/INLINE)';

COMMENT ON TABLE public.prompt_blocks IS '프롬프트 블록(파츠 참조 또는 인라인 텍스트)';

CREATE UNIQUE INDEX pk_prompt_blocks ON public.prompt_blocks
( id );

ALTER TABLE public.prompt_blocks
 ADD CONSTRAINT pk_prompt_blocks PRIMARY KEY 
 USING INDEX pk_prompt_blocks;


DROP TABLE IF EXISTS public.prompts CASCADE;

CREATE TABLE public.prompts
(
    id    UUID DEFAULT gen_random_uuid() NOT NULL,
    workspace_id    UUID NOT NULL,
    title    character varying(100) NOT NULL,
    favorited_at    timestamp with time zone,
    deleted_at    timestamp with time zone,
    purge_at    timestamp with time zone,
    created_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

COMMENT ON COLUMN public.prompts.id IS '프롬프트 ID';

COMMENT ON COLUMN public.prompts.workspace_id IS '워크스페이스 ID';

COMMENT ON COLUMN public.prompts.title IS '제목(100자, 워크스페이스 내 중복 불가)';

COMMENT ON COLUMN public.prompts.favorited_at IS '즐겨찾기 등록 시각';

COMMENT ON COLUMN public.prompts.deleted_at IS 'Soft Delete 시각';

COMMENT ON COLUMN public.prompts.purge_at IS '영구 삭제 예정 시각(deleted_at + 30일)';

COMMENT ON COLUMN public.prompts.created_at IS '생성 시각';

COMMENT ON COLUMN public.prompts.updated_at IS '수정 시각';

COMMENT ON TABLE public.prompts IS '프롬프트(실행 단위)';

CREATE UNIQUE INDEX pk_prompts ON public.prompts
( id );

ALTER TABLE public.prompts
 ADD CONSTRAINT pk_prompts PRIMARY KEY 
 USING INDEX pk_prompts;


DROP TABLE IF EXISTS public.revisions CASCADE;

CREATE TABLE public.revisions
(
    id    UUID DEFAULT gen_random_uuid() NOT NULL,
    entity_type    REVISION_ENTITY_TYPE NOT NULL,
    entity_id    UUID NOT NULL,
    revision_no    integer NOT NULL,
    workspace_id    UUID NOT NULL,
    snapshot    jsonb NOT NULL,
    created_by    UUID,
    created_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

COMMENT ON COLUMN public.revisions.id IS '이력 ID';

COMMENT ON COLUMN public.revisions.entity_type IS '대상 엔티티 종류 (PROMPT/PART/TAG)';

COMMENT ON COLUMN public.revisions.entity_id IS '대상 엔티티 ID (엔티티 영구 삭제 후에도 보존 위해 FK 미연결)';

COMMENT ON COLUMN public.revisions.revision_no IS '엔티티별 버전 번호 (1부터 증가)';

COMMENT ON COLUMN public.revisions.workspace_id IS '워크스페이스 ID (탈퇴 시 일괄 삭제용)';

COMMENT ON COLUMN public.revisions.snapshot IS '스냅샷 (자식 포함, JSONB)';

COMMENT ON COLUMN public.revisions.created_by IS '저장 사용자 ID';

COMMENT ON COLUMN public.revisions.created_at IS '생성 시각';

COMMENT ON TABLE public.revisions IS '편집 이력 (프롬프트/파츠/태그 통합 스냅샷)';

CREATE UNIQUE INDEX pk_revisions ON public.revisions
( id );

ALTER TABLE public.revisions
 ADD CONSTRAINT pk_revisions PRIMARY KEY 
 USING INDEX pk_revisions;


DROP TABLE IF EXISTS public.sample_categories CASCADE;

CREATE TABLE public.sample_categories
(
    id    UUID DEFAULT gen_random_uuid() NOT NULL,
    name    character varying(50) NOT NULL,
    slug    character varying(50) NOT NULL,
    sort_order    integer DEFAULT 0 NOT NULL
);

COMMENT ON COLUMN public.sample_categories.id IS '카테고리 ID';

COMMENT ON COLUMN public.sample_categories.name IS '카테고리명';

COMMENT ON COLUMN public.sample_categories.slug IS 'URL 슬러그';

COMMENT ON COLUMN public.sample_categories.sort_order IS '정렬 순서';

COMMENT ON TABLE public.sample_categories IS '샘플 프롬프트 카테고리';

CREATE UNIQUE INDEX pk_sample_categories ON public.sample_categories
( id );

ALTER TABLE public.sample_categories
 ADD CONSTRAINT pk_sample_categories PRIMARY KEY 
 USING INDEX pk_sample_categories;


DROP TABLE IF EXISTS public.sample_prompts CASCADE;

CREATE TABLE public.sample_prompts
(
    id    UUID DEFAULT gen_random_uuid() NOT NULL,
    category_id    UUID NOT NULL,
    title    character varying(100) NOT NULL,
    description    text,
    body    character varying(700) NOT NULL,
    sort_order    integer DEFAULT 0 NOT NULL,
    is_published    boolean DEFAULT 'true' NOT NULL,
    created_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

COMMENT ON COLUMN public.sample_prompts.id IS '샘플 프롬프트 ID';

COMMENT ON COLUMN public.sample_prompts.category_id IS '카테고리 ID';

COMMENT ON COLUMN public.sample_prompts.title IS '제목';

COMMENT ON COLUMN public.sample_prompts.description IS '설명';

COMMENT ON COLUMN public.sample_prompts.body IS '본문(복사 시 단일 INLINE 블록으로 생성)';

COMMENT ON COLUMN public.sample_prompts.sort_order IS '정렬 순서';

COMMENT ON COLUMN public.sample_prompts.is_published IS '공개 여부';

COMMENT ON COLUMN public.sample_prompts.created_at IS '생성 시각';

COMMENT ON COLUMN public.sample_prompts.updated_at IS '수정 시각';

COMMENT ON TABLE public.sample_prompts IS '샘플 프롬프트(시딩, 갤러리 탐색용)';

CREATE UNIQUE INDEX pk_sample_prompts ON public.sample_prompts
( id );

ALTER TABLE public.sample_prompts
 ADD CONSTRAINT pk_sample_prompts PRIMARY KEY 
 USING INDEX pk_sample_prompts;


DROP TABLE IF EXISTS public.tags CASCADE;

CREATE TABLE public.tags
(
    id    UUID DEFAULT gen_random_uuid() NOT NULL,
    workspace_id    UUID NOT NULL,
    name    character varying(50) NOT NULL,
    created_at    timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

COMMENT ON COLUMN public.tags.id IS '태그 ID';

COMMENT ON COLUMN public.tags.workspace_id IS '워크스페이스 ID';

COMMENT ON COLUMN public.tags.name IS '태그명';

COMMENT ON COLUMN public.tags.created_at IS '생성 시각';

COMMENT ON TABLE public.tags IS '태그';

CREATE UNIQUE INDEX pk_tags ON public.tags
( id );

ALTER TABLE public.tags
 ADD CONSTRAINT pk_tags PRIMARY KEY 
 USING INDEX pk_tags;


DROP TABLE IF EXISTS public.tokens CASCADE;

CREATE TABLE public.tokens
(
    id    UUID DEFAULT gen_random_uuid() NOT NULL,
    user_id    UUID NOT NULL,
    token_hash    character varying(255) NOT NULL,
    expires_at    timestamp with time zone NOT NULL,
    used_at    timestamp with time zone,
    created_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    token_type    TOKEN_TYPE NOT NULL
);

COMMENT ON COLUMN public.tokens.id IS '토큰 ID';

COMMENT ON COLUMN public.tokens.user_id IS '사용자 ID';

COMMENT ON COLUMN public.tokens.token_hash IS '토큰 해시 (원본 토큰은 저장하지 않음)';

COMMENT ON COLUMN public.tokens.expires_at IS '만료 시각';

COMMENT ON COLUMN public.tokens.used_at IS '사용(소비) 시각. NULL이면 미사용';

COMMENT ON COLUMN public.tokens.created_at IS '생성 시각';

COMMENT ON COLUMN public.tokens.token_type IS '토큰 종류 (EMAIL_VERIFICATION/PASSWORD_RESET)';

COMMENT ON TABLE public.tokens IS '단기 인증 토큰 (이메일 인증/비밀번호 재설정 등) 통합 테이블';

CREATE UNIQUE INDEX pk_tokens ON public.tokens
( id );

ALTER TABLE public.tokens
 ADD CONSTRAINT pk_tokens PRIMARY KEY 
 USING INDEX pk_tokens;


DROP TABLE IF EXISTS public.user_identities CASCADE;

CREATE TABLE public.user_identities
(
    id    UUID DEFAULT gen_random_uuid() NOT NULL,
    user_id    UUID NOT NULL,
    provider    AUTH_PROVIDER NOT NULL,
    provider_user_id    character varying(255) NOT NULL,
    access_token    bytea,
    refresh_token    bytea,
    created_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

COMMENT ON COLUMN public.user_identities.id IS '연결 ID';

COMMENT ON COLUMN public.user_identities.user_id IS '사용자 ID';

COMMENT ON COLUMN public.user_identities.provider IS '인증 제공자(EMAIL/GOOGLE)';

COMMENT ON COLUMN public.user_identities.provider_user_id IS '제공자 측 사용자 ID(Google sub 등)';

COMMENT ON COLUMN public.user_identities.access_token IS '액세스 토큰(Revoke용)';

COMMENT ON COLUMN public.user_identities.refresh_token IS '리프레시 토큰';

COMMENT ON COLUMN public.user_identities.created_at IS '생성 시각';

COMMENT ON TABLE public.user_identities IS '사용자 인증 제공자 연결';

CREATE UNIQUE INDEX pk_user_identities ON public.user_identities
( id );

ALTER TABLE public.user_identities
 ADD CONSTRAINT pk_user_identities PRIMARY KEY 
 USING INDEX pk_user_identities;


DROP TABLE IF EXISTS public.user_sessions CASCADE;

CREATE TABLE public.user_sessions
(
    id    UUID DEFAULT gen_random_uuid() NOT NULL,
    user_id    UUID NOT NULL,
    refresh_token_hash    character varying(255) NOT NULL,
    device_info    text,
    expires_at    timestamp with time zone NOT NULL,
    revoked_at    timestamp with time zone,
    created_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

COMMENT ON COLUMN public.user_sessions.id IS '세션 ID';

COMMENT ON COLUMN public.user_sessions.user_id IS '사용자 ID';

COMMENT ON COLUMN public.user_sessions.refresh_token_hash IS '리프레시 토큰 해시';

COMMENT ON COLUMN public.user_sessions.device_info IS '디바이스 정보';

COMMENT ON COLUMN public.user_sessions.expires_at IS '만료 시각';

COMMENT ON COLUMN public.user_sessions.revoked_at IS '폐기 시각(비밀번호 재설정 시 일괄 폐기)';

COMMENT ON COLUMN public.user_sessions.created_at IS '생성 시각';

COMMENT ON TABLE public.user_sessions IS '사용자 세션';

CREATE UNIQUE INDEX pk_user_sessions ON public.user_sessions
( id );

ALTER TABLE public.user_sessions
 ADD CONSTRAINT pk_user_sessions PRIMARY KEY 
 USING INDEX pk_user_sessions;


DROP TABLE IF EXISTS public.users CASCADE;

CREATE TABLE public.users
(
    id    UUID DEFAULT gen_random_uuid() NOT NULL,
    email    CITEXT NOT NULL,
    name    character varying(100) NOT NULL,
    password_hash    character varying(255),
    role    USER_ROLE DEFAULT 'USER'::user_role NOT NULL,
    email_verified_at    timestamp with time zone,
    onboarding_completed_at    timestamp with time zone,
    failed_login_count    integer DEFAULT 0 NOT NULL,
    last_failed_login_at    timestamp with time zone,
    created_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    extension_first_detected_at    timestamp with time zone,
    extension_last_detected_at    timestamp with time zone
);

COMMENT ON COLUMN public.users.id IS '사용자 ID';

COMMENT ON COLUMN public.users.email IS '이메일';

COMMENT ON COLUMN public.users.name IS '이름';

COMMENT ON COLUMN public.users.password_hash IS '비밀번호 해시(이메일 가입자만)';

COMMENT ON COLUMN public.users.role IS '권한(USER/SUPER_ADMIN)';

COMMENT ON COLUMN public.users.email_verified_at IS '이메일 인증 시각';

COMMENT ON COLUMN public.users.onboarding_completed_at IS '온보딩 완료 시각';

COMMENT ON COLUMN public.users.failed_login_count IS '연속 로그인 실패 횟수';

COMMENT ON COLUMN public.users.last_failed_login_at IS '마지막 로그인 실패 시각';

COMMENT ON COLUMN public.users.created_at IS '생성 시각';

COMMENT ON COLUMN public.users.updated_at IS '수정 시각';

COMMENT ON COLUMN public.users.extension_first_detected_at IS '최초 감지 시각';

COMMENT ON COLUMN public.users.extension_last_detected_at IS '최근 감지 시각';

COMMENT ON TABLE public.users IS '사용자';

CREATE UNIQUE INDEX pk_users ON public.users
( id );

ALTER TABLE public.users
 ADD CONSTRAINT pk_users PRIMARY KEY 
 USING INDEX pk_users;


DROP TABLE IF EXISTS public.variables CASCADE;

CREATE TABLE public.variables
(
    entity_type    VARIABLE_ENTITY_TYPE NOT NULL,
    entity_id    UUID NOT NULL,
    name    character varying(100) NOT NULL,
    has_conflict    boolean DEFAULT 'false' NOT NULL
);

COMMENT ON COLUMN public.variables.entity_type IS '대상 엔티티 종류';

COMMENT ON COLUMN public.variables.entity_id IS '대상 엔티티 ID';

COMMENT ON COLUMN public.variables.name IS '변수명';

COMMENT ON COLUMN public.variables.has_conflict IS '변수명 충돌 여부';

COMMENT ON TABLE public.variables IS '변수';

CREATE UNIQUE INDEX pk_variables ON public.variables
( entity_type,entity_id,name );

ALTER TABLE public.variables
 ADD CONSTRAINT pk_variables PRIMARY KEY 
 USING INDEX pk_variables;


DROP TABLE IF EXISTS public.workspaces CASCADE;

CREATE TABLE public.workspaces
(
    id    UUID DEFAULT gen_random_uuid() NOT NULL,
    owner_id    UUID NOT NULL,
    name    character varying(100) DEFAULT '내 워크스페이스' NOT NULL,
    created_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at    timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

COMMENT ON COLUMN public.workspaces.id IS '워크스페이스 ID';

COMMENT ON COLUMN public.workspaces.owner_id IS '소유자 사용자 ID(1:1)';

COMMENT ON COLUMN public.workspaces.name IS '워크스페이스명';

COMMENT ON COLUMN public.workspaces.created_at IS '생성 시각';

COMMENT ON COLUMN public.workspaces.updated_at IS '수정 시각';

COMMENT ON TABLE public.workspaces IS '워크스페이스';

CREATE UNIQUE INDEX pk_workspaces ON public.workspaces
( id );

ALTER TABLE public.workspaces
 ADD CONSTRAINT pk_workspaces PRIMARY KEY 
 USING INDEX pk_workspaces;


-- ============================================================
-- Foreign keys (moved to end to avoid forward-reference errors)
-- ============================================================

ALTER TABLE public.entity_tags
 ADD CONSTRAINT fk_entity_tags_tag FOREIGN KEY ( tag_id )
 REFERENCES tags (id );

ALTER TABLE public.events
 ADD CONSTRAINT fk_events_user FOREIGN KEY ( user_id )
 REFERENCES users (id );

ALTER TABLE public.events
 ADD CONSTRAINT fk_events_workspace FOREIGN KEY ( workspace_id )
 REFERENCES workspaces (id );

ALTER TABLE public.parts
 ADD CONSTRAINT fk_parts_workspace FOREIGN KEY ( workspace_id )
 REFERENCES workspaces (id );

ALTER TABLE public.prompt_blocks
 ADD CONSTRAINT fk_prompt_blocks_part FOREIGN KEY ( part_id )
 REFERENCES parts (id );

ALTER TABLE public.prompt_blocks
 ADD CONSTRAINT fk_prompt_blocks_prompt FOREIGN KEY ( prompt_id )
 REFERENCES prompts (id );

ALTER TABLE public.prompts
 ADD CONSTRAINT fk_prompts_workspace FOREIGN KEY ( workspace_id )
 REFERENCES workspaces (id );

ALTER TABLE public.revisions
 ADD CONSTRAINT fk_revisions_created_by FOREIGN KEY ( created_by )
 REFERENCES users (id );

ALTER TABLE public.revisions
 ADD CONSTRAINT fk_revisions_workspace FOREIGN KEY ( workspace_id )
 REFERENCES workspaces (id );

ALTER TABLE public.sample_prompts
 ADD CONSTRAINT fk_sample_prompts_category FOREIGN KEY ( category_id )
 REFERENCES sample_categories (id );

ALTER TABLE public.tags
 ADD CONSTRAINT fk_tags_workspace FOREIGN KEY ( workspace_id )
 REFERENCES workspaces (id );

ALTER TABLE public.tokens
 ADD CONSTRAINT fk_tokens_user FOREIGN KEY ( user_id )
 REFERENCES users (id );

ALTER TABLE public.user_identities
 ADD CONSTRAINT fk_user_identities_user FOREIGN KEY ( user_id )
 REFERENCES users (id );

ALTER TABLE public.user_sessions
 ADD CONSTRAINT fk_user_sessions_user FOREIGN KEY ( user_id )
 REFERENCES users (id );

ALTER TABLE public.workspaces
 ADD CONSTRAINT fk_workspaces_owner FOREIGN KEY ( owner_id )
 REFERENCES users (id );

-- 컬럼 DEFAULT와 serial 소유 관계를 검사한다. 함수·트리거 내부의 nextval은 별도 검토한다.
-- identity 값은 PostgreSQL이 내부적으로 발급하므로 시퀀스 사용 권한 검사에서 제외한다.
WITH runtime_tables AS (
    SELECT c.oid, n.nspname, c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind IN ('r', 'p')
      AND c.relname IN (
          'users', 'workspaces', 'user_identities', 'user_sessions', 'tokens',
          'login_attempts', 'prompts', 'prompt_blocks', 'variables', 'parts',
          'tags', 'entity_tags'
      )
), required_sequences AS (
    SELECT t.oid AS table_oid, t.nspname AS table_schema, t.relname AS table_name,
           a.attname AS column_name, seq.oid AS sequence_oid,
           sn.nspname AS sequence_schema, seq.relname AS sequence_name
    FROM runtime_tables t
    JOIN pg_attrdef ad ON ad.adrelid = t.oid
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ad.adnum
    JOIN pg_depend d ON d.classid = 'pg_attrdef'::regclass AND d.objid = ad.oid
        AND d.refclassid = 'pg_class'::regclass
    JOIN pg_class seq ON seq.oid = d.refobjid AND seq.relkind = 'S'
    JOIN pg_namespace sn ON sn.oid = seq.relnamespace
    UNION
    SELECT t.oid, t.nspname, t.relname, a.attname, seq.oid, sn.nspname, seq.relname
    FROM runtime_tables t
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum > 0 AND NOT a.attisdropped
    JOIN pg_depend d ON d.refclassid = 'pg_class'::regclass
        AND d.refobjid = t.oid AND d.refobjsubid = a.attnum
        AND d.classid = 'pg_class'::regclass AND d.deptype = 'a'
    JOIN pg_class seq ON seq.oid = d.objid AND seq.relkind = 'S'
    JOIN pg_namespace sn ON sn.oid = seq.relnamespace
)
SELECT current_user AS role_name, table_schema, table_name, column_name,
       sequence_schema, sequence_name,
       has_table_privilege(current_user, table_oid, 'INSERT') AS insert_allowed,
       has_sequence_privilege(current_user, sequence_oid, 'USAGE')
           OR has_sequence_privilege(current_user, sequence_oid, 'UPDATE') AS nextval_allowed
FROM required_sequences
ORDER BY table_schema, table_name, column_name, sequence_name;

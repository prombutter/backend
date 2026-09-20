#!/usr/bin/env bash
# ============================================================
# db/migrations/*.sql 를 대상 DB 에 순서대로 적용한다 — PB-140
#
# 왜 원장(ledger)인가: 이 레포는 Alembic 을 쓰지 않고 번호순 raw SQL 로 스키마를 관리한다
# (db/README.md). 파일이 멱등하게 쓰여 있어도 운영 DB 에 매번 전량을 다시 붓는 것은
# 다른 문제다. 되돌릴 수 없는 DDL 이 하나라도 섞이는 순간 그 방식은 사고가 된다.
# 그래서 적용된 파일을 schema_migrations 에 기록하고, 안 적용된 것만 적용한다.
#
# 사용법:
#   scripts/apply_migrations.sh <DATABASE_URL>              # 미적용분 적용
#   scripts/apply_migrations.sh <DATABASE_URL> --baseline   # 적용 안 하고 적용됨으로만 기록
#   scripts/apply_migrations.sh <DATABASE_URL> --dry-run    # 무엇이 적용될지만 출력
#
# --baseline 은 이미 스키마가 들어 있는 기존 DB 를 원장에 편입시킬 때 딱 한 번 쓴다.
# 실패하면 0 이 아닌 코드로 끝난다. 호출하는 쪽(CI)은 그 뒤 단계를 진행하면 안 된다.
#
# 위치: scripts/apply_migrations.sh
# ============================================================
set -euo pipefail

RAW_URL="${1:-}"
MODE="${2:-apply}"

if [[ -z "$RAW_URL" ]]; then
  echo "사용법: $0 <DATABASE_URL> [--baseline|--dry-run]" >&2
  exit 2
fi

# 앱은 SQLAlchemy 라 postgresql+asyncpg:// 를 쓰지만 psql 은 그 스킴을 모른다.
# 같은 시크릿 하나를 양쪽이 쓰도록 여기서 벗긴다.
PSQL_URL="${RAW_URL/postgresql+asyncpg:\/\//postgresql://}"
PSQL_URL="${PSQL_URL/postgres+asyncpg:\/\//postgresql://}"

MIGRATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/db/migrations"

psql_run() {
  psql "$PSQL_URL" -v ON_ERROR_STOP=1 --no-psqlrc "$@"
}

echo "[migrate] 원장 테이블 확인"
psql_run -q -c "
  create table if not exists public.schema_migrations (
    filename    text        primary key,
    applied_at  timestamptz not null default now(),
    applied_by  text        not null default current_user
  );
"

mapfile -t FILES < <(find "$MIGRATION_DIR" -maxdepth 1 -name '*.sql' -printf '%f\n' | sort)
if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "[migrate] db/migrations 에 SQL 이 없습니다" >&2
  exit 1
fi

PENDING=()
for f in "${FILES[@]}"; do
  seen=$(psql_run -tA -c "select 1 from public.schema_migrations where filename = '$f'")
  if [[ -z "$seen" ]]; then
    PENDING+=("$f")
  fi
done

if [[ ${#PENDING[@]} -eq 0 ]]; then
  echo "[migrate] 적용할 마이그레이션이 없습니다 (총 ${#FILES[@]}건 모두 반영됨)"
  exit 0
fi

echo "[migrate] 미적용 ${#PENDING[@]}건: ${PENDING[*]}"

if [[ "$MODE" == "--dry-run" ]]; then
  echo "[migrate] --dry-run 이라 적용하지 않고 끝냅니다"
  exit 0
fi

for f in "${PENDING[@]}"; do
  if [[ "$MODE" == "--baseline" ]]; then
    echo "[migrate] baseline 기록만: $f"
    psql_run -q -c "insert into public.schema_migrations (filename) values ('$f')"
    continue
  fi

  echo "[migrate] 적용: $f"
  # --single-transaction: SQL 과 원장 기록이 함께 커밋되거나 함께 취소된다.
  # 절반만 적용된 채 원장에는 남는 상태를 만들지 않는다.
  psql_run -q --single-transaction \
    -f "$MIGRATION_DIR/$f" \
    -c "insert into public.schema_migrations (filename) values ('$f')"
  echo "[migrate] 완료: $f"
done

echo "[migrate] 전부 적용됨"

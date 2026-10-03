from pathlib import Path
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db import engine


async def test_login_attempt_sequence_requires_application_role_usage():
    if engine.dialect.name != "postgresql" or engine.url.database not in {
        "prombutter_test",
        "prombutter_ci",
    }:
        pytest.skip("Requires an isolated Prombutter PostgreSQL test database")

    query = (
        Path(__file__).resolve().parents[1] / "scripts/check_runtime_sequence_permissions.sql"
    ).read_text(encoding="utf-8")
    role = f"pb_sequence_test_{uuid.uuid4().hex[:12]}"
    insert = text("""
        INSERT INTO public.login_attempts (success, email_hash)
        VALUES (false, repeat('0', 64)) RETURNING id
    """)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text(f'CREATE ROLE "{role}" NOLOGIN'))
            await connection.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
            await connection.execute(
                text(f'GRANT SELECT, INSERT ON public.login_attempts TO "{role}"')
            )
            await connection.execute(text(f'SET LOCAL ROLE "{role}"'))
            rows = (await connection.execute(text(query))).mappings().all()
            target = next(row for row in rows if row["sequence_name"] == "login_attempts_id_seq")
            assert target["insert_allowed"] is True
            assert target["nextval_allowed"] is False

            savepoint = await connection.begin_nested()
            with pytest.raises(DBAPIError) as failure:
                await connection.execute(insert)
            await savepoint.rollback()
            assert "permission denied for sequence login_attempts_id_seq" in str(failure.value)

            await connection.execute(text("RESET ROLE"))
            await connection.execute(
                text(f'GRANT USAGE ON SEQUENCE public.login_attempts_id_seq TO "{role}"')
            )
            await connection.execute(text(f'SET LOCAL ROLE "{role}"'))
            rows = (await connection.execute(text(query))).mappings().all()
            target = next(row for row in rows if row["sequence_name"] == "login_attempts_id_seq")
            assert target["nextval_allowed"] is True
            assert await connection.scalar(insert) > 0
        finally:
            await transaction.rollback()

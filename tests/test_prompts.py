"""
PB-72 프롬프트 API 테스트

Base: /workspaces/{workspace_id}/prompts (경로 ws 소유 검증)
커버: CRUD·블록(개수/길이/PART참조)·소유검증·복제·즐겨찾기 토글/상한·EXT목록·변수·렌더.
에러코드는 PB-112 에서 통일한 ERR-<접두>-<번호> 규격을 따른다.
제목 중복은 정본(ERR-001 v1.5 §5.4)의 ERR-TITLE-001 에서 ERR-PROMPT-002 로 바뀌었고,
정의서를 새 값으로 업데이트하기로 팀에서 확정했다(2026-08-22).

방식: conftest의 client + make_email 픽스처 사용(실제 로컬 DB, teardown 정리).
위치: tests/test_prompts.py
"""

import uuid

PW = "password123!"  # 8자+ 영문·숫자·특수문자 (인증 명세 1.5)


def _inline(body: str) -> dict:
    return {"block_type": "INLINE", "inline_body": body}


async def _signup_ws(client, make_email) -> str:
    """가입(쿠키 자동 보관) 후 프롬프트 base URL 반환."""
    email = make_email()
    await client.post("/auth/signup", json={"email": email, "password": PW})
    ws_id = (await client.get("/workspaces")).json()["id"]
    return f"/workspaces/{ws_id}/prompts"


# ===== 생성 / 조회 =====
async def test_create_with_blocks_and_get(client, make_email):
    b = await _signup_ws(client, make_email)
    r = await client.post(b, json={"title": "P1", "blocks": [_inline("첫"), _inline("둘")]})
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "P1"
    assert data["favorited_at"] is None
    assert [x["inline_body"] for x in data["blocks"]] == ["첫", "둘"]
    assert [x["sort_order"] for x in data["blocks"]] == [0, 1]

    detail = await client.get(f"{b}/{data['id']}")
    assert detail.status_code == 200
    assert len(detail.json()["blocks"]) == 2


async def test_create_without_blocks_is_draft(client, make_email):
    b = await _signup_ws(client, make_email)
    r = await client.post(b, json={"title": "빈"})
    assert r.status_code == 201
    assert r.json()["blocks"] == []


async def test_list_excludes_deleted(client, make_email):
    b = await _signup_ws(client, make_email)
    pid = (await client.post(b, json={"title": "A"})).json()["id"]
    await client.post(b, json={"title": "B"})
    assert (await client.delete(f"{b}/{pid}")).status_code == 204
    titles = [p["title"] for p in (await client.get(b)).json()]
    assert "A" not in titles and "B" in titles


# ===== 소유 검증 =====
async def test_foreign_workspace_404(client, make_email):
    await _signup_ws(client, make_email)
    r = await client.get(f"/workspaces/{uuid.uuid4()}/prompts")
    assert r.status_code == 404
    assert r.json()["error_code"] == "ERR-WORKSPACE-NOT-FOUND"


async def test_get_missing_prompt_404(client, make_email):
    b = await _signup_ws(client, make_email)
    r = await client.get(f"{b}/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["error_code"] == "ERR-PROMPT-001"


# ===== 제목 중복 / 블록 검증 =====
async def test_duplicate_title_409(client, make_email):
    b = await _signup_ws(client, make_email)
    await client.post(b, json={"title": "같은제목"})
    r = await client.post(b, json={"title": "같은제목"})
    assert r.status_code == 409
    assert r.json()["error_code"] == "ERR-PROMPT-002"


async def test_block_count_over_10_422(client, make_email):
    b = await _signup_ws(client, make_email)
    r = await client.post(b, json={"title": "많음", "blocks": [_inline(str(i)) for i in range(11)]})
    assert r.status_code == 422
    assert r.json()["error_code"] == "ERR-BLOCK-001"


async def test_inline_over_700_422_and_700_ok(client, make_email):
    b = await _signup_ws(client, make_email)
    over = await client.post(b, json={"title": "길다", "blocks": [_inline("x" * 701)]})
    assert over.status_code == 422
    assert over.json()["error_code"] == "ERR-BODY-002"
    ok = await client.post(b, json={"title": "딱맞음", "blocks": [_inline("x" * 700)]})
    assert ok.status_code == 201


async def test_inline_missing_body_422(client, make_email):
    b = await _signup_ws(client, make_email)
    r = await client.post(b, json={"title": "빈블록", "blocks": [{"block_type": "INLINE"}]})
    assert r.status_code == 422
    assert r.json()["error_code"] == "ERR-VAL-001"


async def test_part_block_invalid_ref_422(client, make_email):
    b = await _signup_ws(client, make_email)
    r = await client.post(
        b,
        json={"title": "파츠참조", "blocks": [{"block_type": "PART", "part_id": str(uuid.uuid4())}]},
    )
    assert r.status_code == 422
    assert r.json()["error_code"] == "ERR-BLOCK-002"


# ===== 수정 =====
async def test_update_title_and_blocks_replace(client, make_email):
    b = await _signup_ws(client, make_email)
    pid = (await client.post(b, json={"title": "T", "blocks": [_inline("old")]})).json()["id"]
    r = await client.patch(f"{b}/{pid}", json={"title": "T2", "blocks": [_inline("a"), _inline("b")]})
    assert r.status_code == 200
    assert r.json()["title"] == "T2"
    assert [x["inline_body"] for x in r.json()["blocks"]] == ["a", "b"]


async def test_update_omitting_blocks_keeps_them(client, make_email):
    b = await _signup_ws(client, make_email)
    pid = (await client.post(b, json={"title": "T", "blocks": [_inline("keep")]})).json()["id"]
    r = await client.patch(f"{b}/{pid}", json={"title": "제목만"})
    assert len(r.json()["blocks"]) == 1  # blocks 생략 → 유지


async def test_update_empty_blocks_clears(client, make_email):
    b = await _signup_ws(client, make_email)
    pid = (await client.post(b, json={"title": "T", "blocks": [_inline("x")]})).json()["id"]
    r = await client.patch(f"{b}/{pid}", json={"blocks": []})
    assert r.json()["blocks"] == []  # [] → 전부 삭제


# ===== 복제 =====
async def test_duplicate_copies_blocks_with_new_title(client, make_email):
    b = await _signup_ws(client, make_email)
    pid = (await client.post(b, json={"title": "원본", "blocks": [_inline("a"), _inline("b")]})).json()["id"]

    d1 = await client.post(f"{b}/{pid}/duplicate")
    assert d1.status_code == 201
    assert d1.json()["title"] == "원본 (복사)"
    assert len(d1.json()["blocks"]) == 2
    assert d1.json()["favorited_at"] is None

    d2 = await client.post(f"{b}/{pid}/duplicate")  # 두 번째 복제 → 번호
    assert d2.json()["title"] == "원본 (복사 2)"


# ===== 즐겨찾기 토글 / 상한 =====
async def test_favorite_toggle_on_off(client, make_email):
    b = await _signup_ws(client, make_email)
    pid = (await client.post(b, json={"title": "F"})).json()["id"]
    on = await client.post(f"{b}/{pid}/favorite")
    assert on.status_code == 200 and on.json()["favorited_at"] is not None
    off = await client.post(f"{b}/{pid}/favorite")
    assert off.json()["favorited_at"] is None


async def test_favorite_limit_5_blocks_6th(client, make_email):
    b = await _signup_ws(client, make_email)
    ids = [(await client.post(b, json={"title": f"F{i}"})).json()["id"] for i in range(6)]
    for i in range(5):
        assert (await client.post(f"{b}/{ids[i]}/favorite")).status_code == 200
    r = await client.post(f"{b}/{ids[5]}/favorite")
    assert r.status_code == 422
    assert r.json()["error_code"] == "ERR-FAV-002"


async def test_favorites_list_ext(client, make_email):
    b = await _signup_ws(client, make_email)
    ids = [(await client.post(b, json={"title": f"F{i}"})).json()["id"] for i in range(3)]
    await client.post(f"{b}/{ids[0]}/favorite")
    await client.post(f"{b}/{ids[2]}/favorite")
    r = await client.get(f"{b}/favorites")
    assert r.status_code == 200
    got = {p["id"] for p in r.json()}
    assert got == {ids[0], ids[2]}
    assert all("blocks" not in p for p in r.json())  # 목록은 경량


# ===== 변수 / 렌더 =====
async def test_variables_extracted(client, make_email):
    b = await _signup_ws(client, make_email)
    pid = (await client.post(
        b, json={"title": "V", "blocks": [_inline("{{name}}야 {{lang}}?"), _inline("{{name}} 또")]}
    )).json()["id"]
    r = await client.get(f"{b}/{pid}/variables")
    assert r.json()["variables"] == ["name", "lang"]  # 첫 등장 순, 중복 제거


async def test_render_substitutes_and_reports_missing(client, make_email):
    b = await _signup_ws(client, make_email)
    pid = (await client.post(
        b, json={"title": "V", "blocks": [_inline("안녕 {{name}}, {{lang}}?")]}
    )).json()["id"]

    full = await client.post(f"{b}/{pid}/render", json={"variables": {"name": "붕", "lang": "파이썬"}})
    assert full.status_code == 200
    assert full.json()["rendered"] == "안녕 붕, 파이썬?"
    assert full.json()["missing"] == []

    partial = await client.post(f"{b}/{pid}/render", json={"variables": {"name": "붕"}})
    assert "{{lang}}" in partial.json()["rendered"]  # 값 없는 변수는 자리표시자 유지
    assert partial.json()["missing"] == ["lang"]

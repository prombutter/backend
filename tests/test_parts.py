import pytest
import uuid
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_part_and_variable_count(client: AsyncClient, test_workspace_id: uuid.UUID):
    ws_id = str(test_workspace_id)
    
    # 1. Create a part
    payload = {
        "title": "Test Part 1",
        "body": "This is a body with {{var1}} and {{var2}} and {{var1}}",
        "tags": ["tag1", "tag2"]
    }
    
    res = await client.post(f"/api/v1/workspaces/{ws_id}/parts", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Test Part 1"
    assert data["workspace_id"] == ws_id
    assert "id" in data
    
    # variable_count should be 2 because var1 is duplicated
    assert data["variable_count"] == 2
    assert len(data["tags"]) == 2
    assert "tag1" in data["tags"]

@pytest.mark.asyncio
async def test_part_constraints(client: AsyncClient, test_workspace_id: uuid.UUID):
    ws_id = str(test_workspace_id)
    
    # Exceed title length
    payload_title = {"title": "A" * 101, "body": "Body", "tags": []}
    res = await client.post(f"/api/v1/workspaces/{ws_id}/parts", json=payload_title)
    assert res.status_code in [422, 400]
    
    # Exceed body length
    payload_body = {"title": "Title", "body": "B" * 701, "tags": []}
    res = await client.post(f"/api/v1/workspaces/{ws_id}/parts", json=payload_body)
    assert res.status_code in [422, 400]
    
    # Exceed tag length
    payload_tag = {"title": "Title", "body": "Body", "tags": ["A" * 31]}
    res = await client.post(f"/api/v1/workspaces/{ws_id}/parts", json=payload_tag)
    assert res.status_code in [422, 400]

@pytest.mark.asyncio
async def test_soft_delete_and_restore(client: AsyncClient, test_workspace_id: uuid.UUID):
    ws_id = str(test_workspace_id)
    
    # Create
    res = await client.post(f"/api/v1/workspaces/{ws_id}/parts", json={"title": "T1", "body": "B1"})
    assert res.status_code == 200
    part_id = res.json()["id"]
    
    # List (should appear)
    res = await client.get(f"/api/v1/workspaces/{ws_id}/parts")
    assert len(res.json()) == 1
    
    # Soft delete
    res = await client.delete(f"/api/v1/workspaces/{ws_id}/parts/{part_id}")
    assert res.status_code == 200
    
    # List (should NOT appear)
    res = await client.get(f"/api/v1/workspaces/{ws_id}/parts")
    assert len(res.json()) == 0
    
    # Trash List (should appear)
    res = await client.get(f"/api/v1/workspaces/{ws_id}/parts?is_deleted=true")
    assert len(res.json()) == 1
    
    # Restore
    res = await client.post(f"/api/v1/workspaces/{ws_id}/parts/{part_id}/restore")
    assert res.status_code == 200
    
    # List (should appear again)
    res = await client.get(f"/api/v1/workspaces/{ws_id}/parts")
    assert len(res.json()) == 1

@pytest.mark.asyncio
async def test_permanent_delete(client: AsyncClient, test_workspace_id: uuid.UUID):
    ws_id = str(test_workspace_id)
    
    # Create
    res = await client.post(f"/api/v1/workspaces/{ws_id}/parts", json={"title": "T1", "body": "B1"})
    part_id = res.json()["id"]
    
    # Soft delete
    await client.delete(f"/api/v1/workspaces/{ws_id}/parts/{part_id}")
    
    # Permanent delete
    res = await client.delete(f"/api/v1/workspaces/{ws_id}/parts/{part_id}/permanent")
    assert res.status_code == 200
    
    # Trash List (should NOT appear)
    res = await client.get(f"/api/v1/workspaces/{ws_id}/parts?is_deleted=true")
    assert len(res.json()) == 0
    
    # Also verify getting specific part returns 404
    res = await client.get(f"/api/v1/workspaces/{ws_id}/parts/{part_id}")
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_toggle_favorite(client: AsyncClient, test_workspace_id: uuid.UUID):
    ws_id = str(test_workspace_id)
    
    # Create
    res = await client.post(f"/api/v1/workspaces/{ws_id}/parts", json={"title": "Fav Test", "body": "B1"})
    part_id = res.json()["id"]
    assert res.json()["is_favorite"] is False
    
    # Toggle (False -> True)
    res = await client.post(f"/api/v1/workspaces/{ws_id}/parts/{part_id}/favorite")
    assert res.status_code == 200
    assert res.json()["is_favorite"] is True
    
    # Toggle (True -> False)
    res = await client.post(f"/api/v1/workspaces/{ws_id}/parts/{part_id}/favorite")
    assert res.status_code == 200
    assert res.json()["is_favorite"] is False

@pytest.mark.asyncio
async def test_parts_unauthorized_401(client: AsyncClient, test_workspace_id: uuid.UUID):
    ws_id = str(test_workspace_id)
    # Clear cookies to simulate unauthenticated user
    client.cookies.clear()
    
    # Try to access list_parts
    res = await client.get(f"/api/v1/workspaces/{ws_id}/parts")
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_parts_forbidden_workspace_404(client: AsyncClient, test_workspace_id: uuid.UUID):
    # Try to access a random workspace ID
    random_ws_id = str(uuid.uuid4())
    
    res = await client.get(f"/api/v1/workspaces/{random_ws_id}/parts")
    # According to get_path_workspace, this should return 404
    assert res.status_code == 404

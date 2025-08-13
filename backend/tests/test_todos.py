import pytest
from httpx import AsyncClient
from fastapi import FastAPI
from unittest.mock import AsyncMock
from bson import ObjectId
import mongomock
from motor.motor_asyncio import AsyncIOMotorClient

from src.mysite.main import app, todos

@pytest.fixture(autouse=True)
def mock_mongo(monkeypatch):
    """Replace MongoDB collection with an in-memory mongomock."""
    mock_client = mongomock.MongoClient()
    mock_db = mock_client["todo_db"]
    mock_collection = mock_db["todos"]

    # Wrap mongomock methods with AsyncMock to simulate async motor behavior
    async def insert_one(doc):
        result = mock_collection.insert_one(doc)
        return type("InsertResult", (), {"inserted_id": result.inserted_id})

    async def find_one(filter):
        return mock_collection.find_one(filter)

    async def find():
        return list(mock_collection.find())

    async def delete_one(filter):
        result = mock_collection.delete_one(filter)
        return type("DeleteResult", (), {"deleted_count": result.deleted_count})

    todos.insert_one = insert_one
    todos.find_one = find_one
    todos.find = lambda: AsyncMock(to_list=lambda length=None: list(mock_collection.find()))
    todos.delete_one = delete_one

    yield

@pytest.mark.asyncio
async def test_create_todo():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/todos", json={"content": "Test todo"})
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Test todo"
    assert "_id" in data or "id" in data

@pytest.mark.asyncio
async def test_read_todos():
    # First, add a todo
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post("/todos", json={"content": "Another todo"})
        response = await ac.get("/todos")
    assert response.status_code == 200
    todos_list = response.json()
    assert len(todos_list) >= 1
    assert todos_list[0]["content"] == "Another todo"

@pytest.mark.asyncio
async def test_delete_todo():
    # Create a todo
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_res = await ac.post("/todos", json={"content": "Delete me"})
        todo_id = create_res.json()["id"]

        delete_res = await ac.delete(f"/todos/{todo_id}")
    assert delete_res.status_code == 200
    assert delete_res.json()["message"] == "Todo deleted successfully"

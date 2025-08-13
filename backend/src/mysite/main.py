from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, info):
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        if isinstance(value, ObjectId):
            return value
        return ObjectId(value)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema):
        from pydantic import core_schema
        return core_schema.str_schema()


# Modèle TodoItem avec gestion de l'ID MongoDB
class TodoItem(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    content: str

    model_config = {
        "json_encoders": {ObjectId: str},
        "populate_by_name": True,
    }

class TodoItemCreate(BaseModel):
    content: str

MONGO_CONNECTION_STRING = os.environ["MONGO_CONNECTION_STRING"]

client = AsyncIOMotorClient(MONGO_CONNECTION_STRING, uuidRepresentation='standard')
db = client.todo_db
todos = db.todos

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
def serve_html():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Todo List</title>
    </head>
    <body>
        <h1>Todo List</h1>
        <input type="text" id="newItem" placeholder="Enter a new item">
        <button onclick="addItem()">Add</button>
        <ul id="todoList"></ul>

        <script>
        const API_URL = 'http://localhost:8000';
        const list = document.getElementById('todoList');

        async function fetchTodos() {
          const response = await fetch(`${API_URL}/todos`);
          const todos = await response.json();
          list.innerHTML = '';
          todos.forEach(todo => addTodoToUI(todo));
        }

        function addTodoToUI(todo) {
          const li = document.createElement('li');
          li.textContent = todo.content + ' ';
          const deleteBtn = document.createElement('button');
          deleteBtn.textContent = 'Delete';
          deleteBtn.onclick = async () => {
            await fetch(`${API_URL}/todos/${todo.id}`, { method: 'DELETE' });
            list.removeChild(li);
          };
          li.appendChild(deleteBtn);
          list.appendChild(li);
        }

        async function addItem() {
          const input = document.getElementById('newItem');
          const content = input.value.trim();
          if (!content) return;
          const res = await fetch(`${API_URL}/todos`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
          });
          const newTodo = await res.json();
          addTodoToUI(newTodo);
          input.value = '';
        }

        fetchTodos();
        </script>
    </body>
    </html>
    """

@app.post("/todos", response_model=TodoItem)
async def create_todo(item: TodoItemCreate):
    todo_doc = item.dict()
    result = await todos.insert_one(todo_doc)
    created = await todos.find_one({"_id": result.inserted_id})
    return created

@app.get("/todos", response_model=list[TodoItem])
async def read_todos():
    todos_list = await todos.find().to_list(length=None)
    return todos_list

@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: str):
    if not ObjectId.is_valid(todo_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    delete_result = await todos.delete_one({"_id": ObjectId(todo_id)})
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Todo not found")
    return {"message": "Todo deleted successfully"}

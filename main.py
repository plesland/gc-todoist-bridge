import os
import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

TODOIST_API_TOKEN = os.environ.get("TODOIST_API_TOKEN")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY")

if not TODOIST_API_TOKEN or not INTERNAL_API_KEY:
    raise RuntimeError("Missing required environment variables")

app = FastAPI()


class TaskRequest(BaseModel):
    content: str
    due_string: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/task")
def create_task(
    task: TaskRequest,
    x_api_key: str = Header(...)
):
    # Internal auth check
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not task.content or not task.content.strip():
        raise HTTPException(status_code=400, detail="Task content is required")

    payload = {
        "content": task.content
    }

    if task.due_string:
        payload["due_string"] = task.due_string

    response = requests.post(
        "https://api.todoist.com/rest/v2/tasks",
        headers={
            "Authorization": f"Bearer {TODOIST_API_TOKEN}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=10
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()
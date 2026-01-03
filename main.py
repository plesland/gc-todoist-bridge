from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import requests
import os

app = FastAPI(title="Todoist Bridge", version="1.0.0")

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")
TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")

TODOIST_API_URL = "https://api.todoist.com/rest/v2/tasks"


class TaskRequest(BaseModel):
    content: str = Field(..., description="The task title")
    due_string: str | None = Field(
        None,
        description="Natural language due date, e.g. 'tomorrow'"
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/task")
def create_task(
    task: TaskRequest,
    x_api_key: str = Header(None)
):
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not task.content or not task.content.strip():
        raise HTTPException(status_code=400, detail="Missing task content")

    payload = {"content": task.content}
    if task.due_string:
        payload["due_string"] = task.due_string

    response = requests.post(
        TODOIST_API_URL,
        headers={
            "Authorization": f"Bearer {TODOIST_API_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=response.text,
        )

    return response.json()
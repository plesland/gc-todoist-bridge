import os
import requests
from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

TODOIST_API_TOKEN = os.environ.get("TODOIST_API_TOKEN")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY")

if not TODOIST_API_TOKEN or not INTERNAL_API_KEY:
    raise RuntimeError("Missing required environment variables")

TODOIST_HEADERS = {
    "Authorization": f"Bearer {TODOIST_API_TOKEN}",
    "Content-Type": "application/json"
}

app = FastAPI()


class TaskRequest(BaseModel):
    content: str
    due_string: Optional[str] = None
    labels: Optional[List[str]] = None


class TaskUpdateRequest(BaseModel):
    content: Optional[str] = None
    due_string: Optional[str] = None
    labels: Optional[List[str]] = None


def auth_check(x_api_key: str):
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/task")
def create_task(
    task: TaskRequest,
    x_api_key: str = Header(...)
):
    auth_check(x_api_key)

    payload = {"content": task.content}

    if task.due_string:
        payload["due_string"] = task.due_string

    # Always label GC-managed tasks
    labels = set(task.labels or [])
    labels.add("gc-project")
    payload["labels"] = list(labels)

    r = requests.post(
        "https://api.todoist.com/rest/v2/tasks",
        headers=TODOIST_HEADERS,
        json=payload,
        timeout=10
    )

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return r.json()


@app.get("/tasks")
def list_tasks(
    label: Optional[str] = Query(None),
    x_api_key: str = Header(...)
):
    auth_check(x_api_key)

    params = {}
    if label:
        params["label"] = label

    r = requests.get(
        "https://api.todoist.com/rest/v2/tasks",
        headers=TODOIST_HEADERS,
        params=params,
        timeout=10
    )

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return r.json()


@app.patch("/task/{task_id}")
def update_task(
    task_id: str,
    task: TaskUpdateRequest,
    x_api_key: str = Header(...)
):
    auth_check(x_api_key)

    payload = {}

    if task.content:
        payload["content"] = task.content
    if task.due_string:
        payload["due_string"] = task.due_string
    if task.labels is not None:
        payload["labels"] = task.labels

    r = requests.post(
        f"https://api.todoist.com/rest/v2/tasks/{task_id}",
        headers=TODOIST_HEADERS,
        json=payload,
        timeout=10
    )

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return r.json()


@app.post("/task/{task_id}/close")
def close_task(
    task_id: str,
    x_api_key: str = Header(...)
):
    auth_check(x_api_key)

    r = requests.post(
        f"https://api.todoist.com/rest/v2/tasks/{task_id}/close",
        headers=TODOIST_HEADERS,
        timeout=10
    )

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return {"status": "closed"}
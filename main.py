from fastapi import FastAPI, Header, HTTPException
import requests
import os

app = FastAPI()

TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

TODOIST_API_BASE = "https://api.todoist.com/rest/v2"


def auth_check(x_api_key: str | None):
    if INTERNAL_API_KEY and x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/projects")
def create_project(name: str, x_api_key: str | None = Header(None)):
    auth_check(x_api_key)

    r = requests.post(
        f"{TODOIST_API_BASE}/projects",
        headers={
            "Authorization": f"Bearer {TODOIST_API_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"name": name},
    )

    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=r.text)

    return r.json()


@app.post("/tasks")
def create_task(
    content: str,
    project_id: str,
    due_string: str | None = None,
    x_api_key: str | None = Header(None),
):
    auth_check(x_api_key)

    payload = {
        "content": content,
        "project_id": project_id,
    }

    if due_string:
        payload["due_string"] = due_string

    r = requests.post(
        f"{TODOIST_API_BASE}/tasks",
        headers={
            "Authorization": f"Bearer {TODOIST_API_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
    )

    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=r.text)

    return r.json()

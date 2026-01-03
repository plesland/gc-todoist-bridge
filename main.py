from fastapi import FastAPI, Header, HTTPException
import requests
import os

app = FastAPI()

TODOIST_TOKEN = os.getenv("TODOIST_API_TOKEN")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

TODOIST_API = "https://api.todoist.com/rest/v2"

@app.get("/")
def health():
    return {"status": "ok"}

def auth_internal(key: str | None):
    if not INTERNAL_API_KEY or key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

@app.post("/task")
def create_task(
    content: str,
    authorization: str | None = Header(default=None)
):
    auth_internal(authorization)

    if not TODOIST_TOKEN:
        raise HTTPException(status_code=500, detail="Todoist token missing")

    r = requests.post(
        f"{TODOIST_API}/tasks",
        headers={
            "Authorization": f"Bearer {TODOIST_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"content": content},
        timeout=10,
    )

    if r.status_code != 200:
        raise HTTPException(status_code=500, detail=r.text)

    return r.json()
# main.py
import os
import io
import requests
import pandas as pd
import matplotlib.pyplot as plt
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from db import get_conn

from strava import router as strava_router
from strava import list_activities  # For reuse inside training-load endpoints

# -------------------------
# Environment Variables
# -------------------------

TODOIST_API_TOKEN = os.environ.get("TODOIST_API_TOKEN")
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY")

TODOIST_HEADERS = {
    "Authorization": f"Bearer {TODOIST_API_TOKEN}" if TODOIST_API_TOKEN else "",
    "Content-Type": "application/json"
}

app = FastAPI()
app.include_router(strava_router)

# -------------------------
# Models
# -------------------------

class TaskRequest(BaseModel):
    content: str
    due_string: Optional[str] = None
    labels: Optional[List[str]] = None


class TaskUpdateRequest(BaseModel):
    content: Optional[str] = None
    due_string: Optional[str] = None
    labels: Optional[List[str]] = None


# -------------------------
# Auth / Config
# -------------------------

def auth_check(x_api_key: str):
    if not INTERNAL_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: INTERNAL_API_KEY missing"
        )

    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not TODOIST_API_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: TODOIST_API_TOKEN missing"
        )


# -------------------------
# Health Endpoint
# -------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "todoist_token_present": bool(TODOIST_API_TOKEN),
        "internal_key_present": bool(INTERNAL_API_KEY)
    }


# -------------------------
# TODOIST: Task Management
# -------------------------

@app.post("/task")
def create_task(task: TaskRequest, x_api_key: str = Header(...)):
    auth_check(x_api_key)

    payload = {"content": task.content}
    if task.due_string:
        payload["due_string"] = task.due_string

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
def list_tasks(label: Optional[str] = Query(None), x_api_key: str = Header(...)):
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
def update_task(task_id: str, task: TaskUpdateRequest, x_api_key: str = Header(...)):
    auth_check(x_api_key)

    payload = {}
    if task.content is not None:
        payload["content"] = task.content
    if task.due_string is not None:
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
def close_task(task_id: str, x_api_key: str = Header(...)):
    auth_check(x_api_key)

    r = requests.post(
        f"https://api.todoist.com/rest/v2/tasks/{task_id}/close",
        headers=TODOIST_HEADERS,
        timeout=10
    )

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    return {"status": "closed"}


@app.get("/tasks/summary")
def task_summary(x_api_key: str = Header(...)):
    auth_check(x_api_key)

    r = requests.get(
        "https://api.todoist.com/rest/v2/tasks",
        headers=TODOIST_HEADERS,
        params={"label": "gc-project"},
        timeout=10
    )

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    tasks = r.json()
    now = datetime.utcnow()
    soon = now + timedelta(days=5)

    summary = {"overdue": [], "blocking": [], "due_soon": [], "inspections": []}

    for t in tasks:
        labels = set(t.get("labels", []))
        due = t.get("due")

        if "blocking" in labels:
            summary["blocking"].append(t)
        if "inspection" in labels:
            summary["inspections"].append(t)

        if due and due.get("date"):
            try:
                due_date = datetime.fromisoformat(due["date"].replace("Z", ""))
                if due_date < now:
                    summary["overdue"].append(t)
                elif due_date <= soon:
                    summary["due_soon"].append(t)
            except ValueError:
                pass

    return summary


# -------------------------
# TRAINING LOAD ENDPOINTS
# -------------------------

@app.get("/training-load")
def training_load(days: int = 42, x_api_key: str = Header(...)):
    """
    Returns CTL, ATL, TSB, and trend summary for recent Strava activities.
    """
    auth_check(x_api_key)
    data = list_activities(days=days, x_api_key=x_api_key)
    training_load = data.get("training_load")

    if not training_load:
        raise HTTPException(status_code=404, detail="No training load data found")

    return training_load

@app.get("/training-load/history")
def training_load_history(limit: int = 90, x_api_key: str = Header(...)):
    """
    Returns stored training load history (CTL/ATL/TSB) from the database.
    """
    auth_check(x_api_key)

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT date, tss, ctl, atl, tsb
            FROM training_load
            ORDER BY date DESC
            LIMIT ?
        """, (limit,)).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No stored training data found")

    return [dict(r) for r in rows]

@app.get("/training-load/chart")
def training_load_chart(days: int = 42, x_api_key: str = Header(...)):
    """
    Returns a PNG chart of CTL/ATL/TSB over the past period.
    """
    auth_check(x_api_key)
    data = list_activities(days=days, x_api_key=x_api_key)
    load = data.get("training_load")

    if not load or "history" not in load:
        raise HTTPException(status_code=400, detail="no load data")

    df = pd.DataFrame(load["history"])
    plt.figure(figsize=(8, 4))
    plt.plot(df["date"], df["ctl"], label="CTL (42d)")
    plt.plot(df["date"], df["atl"], label="ATL (7d)")
    plt.plot(df["date"], df["tsb"], label="TSB", linestyle="--")
    plt.legend()
    plt.title("Training Load Trends")
    plt.xlabel("Date")
    plt.ylabel("Score")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close()
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
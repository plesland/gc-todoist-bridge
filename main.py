import os
import requests
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional

# ------------------------------------------------------------------
# Environment variables (must exist in DigitalOcean App settings)
# ------------------------------------------------------------------

TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

if not TODOIST_API_TOKEN:
    raise RuntimeError("Missing TODOIST_API_TOKEN environment variable")

if not INTERNAL_API_KEY:
    raise RuntimeError("Missing INTERNAL_API_KEY environment variable")

# ------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------

app = FastAPI(
    title="GC Todoist Bridge",
    description="Private API bridge between ChatGPT and Todoist",
    version="1.0.0",
)

# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------

class TaskCreateRequest(BaseModel):
    content: str = Field(..., description="The task title")
    due_string: Optional[str] = Field(
        None,
        description="Natural language due date (e.g. 'tomorrow', 'next Monday')",
    )


class TaskCreateResponse(BaseModel):
    id: str
    content: str


# ------------------------------------------------------------------
# Auth helper
# ------------------------------------------------------------------

def verify_internal_key(x_api_key: str):
    if x_api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post(
    "/task",
    response_model=TaskCreateResponse,
    summary="Create Todoist task",
    description="Creates a task in Todoist using the REST API",
)
def create_task(
    task: TaskCreateRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    # ------------------------------------------------------------------
    # Authenticate caller (ChatGPT Custom GPT)
    # ------------------------------------------------------------------
    verify_internal_key(x_api_key)

    # ------------------------------------------------------------------
    # Build Todoist payload
    # ------------------------------------------------------------------
    payload = {
        "content": task.content,
    }

    if task.due_string:
        payload["due_string"] = task.due_string

    # ------------------------------------------------------------------
    # Call Todoist API
    # ------------------------------------------------------------------
    response = requests.post(
        "https://api.todoist.com/rest/v2/tasks",
        headers={
            "Authorization": f"Bearer {TODOIST_API_TOKEN}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "Todoist API call failed",
                "status_code": response.status_code,
                "response": response.text,
            },
        )

    data = response.json()

    return {
        "id": data["id"],
        "content": data["content"],
    }
# strava.py
from fastapi import APIRouter, Header, HTTPException
import requests
from datetime import datetime, timedelta
from strava_client import get_access_token, exchange_code_for_token
from auth import auth_check  # adjust import if needed
from training_load import compute_training_load  # NEW import

router = APIRouter(prefix="/strava", tags=["strava"])


@router.get("/oauth/callback")
def strava_oauth_callback(code: str, scope: str = None, state: str = None):
    """Handle OAuth callback from Strava."""
    return exchange_code_for_token(code)


@router.get("/activities")
def list_activities(
    days: int = 7,
    x_api_key: str = Header(...)
):
    """
    Fetch Strava activities within the past N days.
    Adds Training Load metrics (hrTSS, rTSS, CTL, ATL, TSB).
    """
    auth_check(x_api_key)

    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="days must be between 1 and 90")

    token = get_access_token()
    if isinstance(token, dict):
        raise HTTPException(status_code=500, detail=token)

    after_ts = int((datetime.utcnow() - timedelta(days=days)).timestamp())

    resp = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params={"after": after_ts, "per_page": 200},
        timeout=10,
    )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    raw_activities = resp.json()
    activities = []

    for a in raw_activities:
        activities.append({
            "id": a["id"],
            "type": a["type"],
            "distance_m": a["distance"],
            "moving_time_s": a["moving_time"],
            "average_hr": a.get("average_heartrate"),
            "start_date": a["start_date"],
        })

    # Compute training load metrics
    try:
        training_load = compute_training_load(activities)
    except Exception as e:
        training_load = {"error": f"training_load_failed: {str(e)}"}

    return {
        "days": days,
        "count": len(activities),
        "activities": activities,
        "training_load": training_load
    }


@router.get("/latest-activity")
def latest_activity(x_api_key: str = Header(...)):
    """
    Fetch the most recent Strava activity.
    """
    auth_check(x_api_key)

    token = get_access_token()
    if isinstance(token, dict):
        raise HTTPException(status_code=500, detail=token)

    resp = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params={"per_page": 1},
        timeout=10,
    )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    if not data:
        return {"message": "no activities found"}

    a = data[0]
    return {
        "id": a["id"],
        "type": a["type"],
        "distance_m": a["distance"],
        "moving_time_s": a["moving_time"],
        "average_hr": a.get("average_heartrate"),
        "start_date": a["start_date"],
    }
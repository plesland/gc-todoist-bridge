from fastapi import APIRouter, Header, HTTPException
import requests
from datetime import datetime, timedelta
from strava_client import get_access_token, exchange_code_for_token
from auth import auth_check  # adjust import if needed

router = APIRouter(prefix="/strava", tags=["strava"])


@router.get("/oauth/callback")
def strava_oauth_callback(code: str, scope: str = None, state: str = None):
    return exchange_code_for_token(code)


@router.get("/activities")
def list_activities(
    days: int = 7,
    x_api_key: str = Header(...)
):
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

    activities = [{
        "id": a["id"],
        "type": a["type"],
        "distance_m": a["distance"],
        "moving_time_s": a["moving_time"],
        "average_hr": a.get("average_heartrate"),
        "start_date": a["start_date"],
    } for a in resp.json()]

    return {
        "days": days,
        "count": len(activities),
        "activities": activities
    }


@router.get("/latest-activity")
def latest_activity(x_api_key: str = Header(...)):
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
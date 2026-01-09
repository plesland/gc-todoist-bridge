from fastapi import APIRouter
import requests
from strava_client import get_access_token
from strava_client import exchange_code_for_token

router = APIRouter(prefix="/strava", tags=["strava"])

@router.get("/oauth/callback")
def strava_oauth_callback(code: str, scope: str = None, state: str = None):
    return exchange_code_for_token(code)

@router.get("/oauth")
def strava_oauth(code: str):
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
        params={
            "after": after_ts,
            "per_page": 200
        },
        timeout=10,
    )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    activities = []
    for a in resp.json():
        activities.append({
            "id": a["id"],
            "type": a["type"],
            "distance_m": a["distance"],
            "moving_time_s": a["moving_time"],
            "average_hr": a.get("average_heartrate"),
            "start_date": a["start_date"],
        })

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
        return token

    resp = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params={"per_page": 1},
        timeout=10,
    )

    if resp.status_code != 200:
        return {
            "error": "strava_api_error",
            "status": resp.status_code,
            "body": resp.text,
        }

    data = resp.json()

    if not data:
        return {"message": "no activities found"}

    activity = data[0]

    return {
        "id": activity["id"],
        "type": activity["type"],
        "distance_m": activity["distance"],
        "moving_time_s": activity["moving_time"],
        "average_hr": activity.get("average_heartrate"),
        "start_date": activity["start_date"],
    }
    
def oauth_callback(code: str):
    import requests
    import os

    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": os.environ["STRAVA_CLIENT_ID"],
            "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )

    return resp.json()
    
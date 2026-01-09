from fastapi import APIRouter
import requests
from strava_client import get_access_token

router = APIRouter(prefix="/strava", tags=["strava"])

@router.get("/latest-activity")
def latest_activity():
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
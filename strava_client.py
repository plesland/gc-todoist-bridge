import os
import requests

STRAVA_CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")
STRAVA_REFRESH_TOKEN = os.environ.get("STRAVA_REFRESH_TOKEN")


def get_access_token():
    missing = []
    if not STRAVA_CLIENT_ID:
        missing.append("STRAVA_CLIENT_ID")
    if not STRAVA_CLIENT_SECRET:
        missing.append("STRAVA_CLIENT_SECRET")
    if not STRAVA_REFRESH_TOKEN:
        missing.append("STRAVA_REFRESH_TOKEN")

    if missing:
        return {
            "error": "missing_env_vars",
            "missing": missing,
        }

    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "refresh_token": STRAVA_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )

    if resp.status_code != 200:
        return {
            "error": "strava_token_error",
            "status_code": resp.status_code,
            "response": resp.text,
        }

    return resp.json().get("access_token")
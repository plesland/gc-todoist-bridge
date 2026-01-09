# auth.py
import os
from fastapi import Header, HTTPException

def auth_check(x_api_key: str = Header(...)):
    """
    Simple API key header validation.
    Checks the provided 'x-api-key' header against the environment variable API_KEY.
    Raises HTTP 401 if missing or invalid.
    """

    expected_key = os.getenv("API_KEY")

    # If no key is configured, fail early (to avoid open access)
    if not expected_key:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: API_KEY environment variable not set."
        )

    # Compare incoming key to stored one
    if x_api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key."
        )

    # Return True (optional, since FastAPI will continue execution)
    return True
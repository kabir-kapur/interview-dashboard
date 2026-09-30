"""HTTP Basic authentication for the single-user API."""

import os
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials


security = HTTPBasic(auto_error=False)


def require_api_auth(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(security)],
) -> str:
    """Require configured credentials without exposing which value was wrong."""
    expected_username = os.getenv("BASIC_AUTH_USERNAME")
    expected_password = os.getenv("BASIC_AUTH_PASSWORD")
    if not expected_username or not expected_password:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "API authentication is not configured")

    valid = credentials and secrets.compare_digest(credentials.username, expected_username) and secrets.compare_digest(
        credentials.password, expected_password
    )
    if not valid:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

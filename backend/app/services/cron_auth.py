"""Authentication for scheduled jobs invoked by Vercel."""

import os
import secrets
from typing import Annotated

from fastapi import Header, HTTPException


def require_cron_secret(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Require Vercel's Bearer CRON_SECRET without accepting browser auth."""
    expected_secret = os.getenv("CRON_SECRET")
    scheme, _, provided_secret = (authorization or "").partition(" ")
    if not expected_secret:
        raise HTTPException(503, "Cron authentication is not configured")
    if scheme.lower() != "bearer" or not secrets.compare_digest(provided_secret, expected_secret):
        raise HTTPException(401, "Invalid cron credentials")

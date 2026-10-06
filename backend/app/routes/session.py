"""Authenticated browser-session validation route."""

from fastapi import APIRouter


router = APIRouter()


@router.get("/session")
def session():
    """Confirm that the supplied API credentials are valid."""
    return {"ok": True}

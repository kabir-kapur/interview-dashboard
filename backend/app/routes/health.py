"""Public health-check route."""

from fastapi import APIRouter


router = APIRouter()


@router.get("/api/health")
def health():
    """Report that the application is accepting requests."""
    return {"ok": True}

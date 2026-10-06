"""FastAPI application setup and route registration."""

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.config import cors_origins
from app.routes import cron, daily_plans, health, problems, session, submissions
from app.services.auth import require_api_auth
from app.services.database import run_migrations


app = FastAPI(title="Interview Console API")
app.add_middleware(CORSMiddleware, allow_origins=cors_origins(), allow_methods=["*"], allow_headers=["*"])

api = APIRouter(prefix="/api", dependencies=[Depends(require_api_auth)])
api.include_router(session.router)
api.include_router(daily_plans.router)
api.include_router(problems.router)
api.include_router(submissions.router)

app.include_router(health.router)
app.include_router(cron.router)
app.include_router(api)


@app.on_event("startup")
def startup():
    """Ensure the configured database has every known schema migration."""
    run_migrations(config.DB)

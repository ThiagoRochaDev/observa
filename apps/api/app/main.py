from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.db import init_db
from app.core.security import get_or_create_api_key
from app.presentation.api.auth_flow_router import router as auth_flow_router
from app.presentation.api.router import router

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    get_or_create_api_key()  # prints the token to the log on first boot
    try:
        from app.application.sync_service import ensure_full_demo

        result = ensure_full_demo()
        print(f"[observa] demo seed: {result}")
    except Exception as exc:  # noqa: BLE001
        print(f"[observa] demo seed failed: {exc}")
    yield


app = FastAPI(
    title=settings.app_name,
    description="Observa — connect clouds, catalog products, cost & health",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
# Deliberately outside /api (unauthenticated by design — see
# auth_flow_router.py's module docstring): a browser hits these to GET a
# credential in the first place, matching the redirect_uri the settings
# page defaults providers to (http://localhost:8080/auth/callback/{provider}).
app.include_router(auth_flow_router)


@app.get("/")
def root():
    return {
        "app": "observa",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/healthz")
def healthz():
    """Unauthenticated liveness probe (Docker/orchestrator healthcheck) —
    deliberately outside /api, which requires the API key on every route."""
    return {"status": "ok"}

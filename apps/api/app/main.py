from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.db import init_db
from app.presentation.api.router import router

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
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


@app.get("/")
def root():
    return {
        "app": "observa",
        "docs": "/docs",
        "health": "/api/health",
    }

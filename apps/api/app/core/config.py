from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[4]  # observa/
DATA_DIR = ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Observa"
    environment: str = "development"
    data_dir: Path = DATA_DIR
    database_path: Path | None = None
    # Fernet key for encrypting connector secrets (generated & persisted on first boot)
    secrets_key_file: Path | None = None
    # Shared token required on every /api request (generated & persisted on first boot)
    api_key_file_path: Path | None = None
    # HS256 secret for OIDC-mode session tokens (generated & persisted on first boot)
    session_secret_file_path: Path | None = None
    # In production, inject secrets through the runtime secret manager instead
    # of generating them inside the application volume.
    observa_api_key: str | None = None
    observa_secrets_key: str | None = None
    observa_session_secret: str | None = None
    seed_demo_data: bool = True
    enable_api_docs: bool = True
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 240
    rate_limit_window_seconds: int = 60
    auth_rate_limit_requests: int = 30
    max_request_body_bytes: int = 2_000_000
    trust_proxy_headers: bool = False
    # Where to bounce the browser back to once the OIDC callback finishes —
    # the Next.js app (not the API itself). Override in prod (e.g. behind a
    # reverse proxy / real domain) via FRONTEND_URL.
    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @property
    def db_path(self) -> Path:
        return self.database_path or (self.data_dir / "observa.db")

    @property
    def key_file(self) -> Path:
        return self.secrets_key_file or (self.data_dir / "secrets.key")

    @property
    def api_key_file(self) -> Path:
        return self.api_key_file_path or (self.data_dir / "api_key")

    @property
    def session_secret_file(self) -> Path:
        return self.session_secret_file_path or (self.data_dir / "session_secret")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    return s


def validate_production_settings(settings: Settings) -> None:
    if settings.environment.lower() != "production":
        return
    missing = [
        name
        for name, value in {
            "OBSERVA_API_KEY": settings.observa_api_key,
            "OBSERVA_SECRETS_KEY": settings.observa_secrets_key,
            "OBSERVA_SESSION_SECRET": settings.observa_session_secret,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Production requires externally managed secrets: " + ", ".join(missing)
        )
    if len(settings.observa_api_key or "") < 32:
        raise RuntimeError("OBSERVA_API_KEY must contain at least 32 characters")
    if len(settings.observa_session_secret or "") < 32:
        raise RuntimeError("OBSERVA_SESSION_SECRET must contain at least 32 characters")
    try:
        Fernet((settings.observa_secrets_key or "").encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("OBSERVA_SECRETS_KEY must be a valid Fernet key") from exc
    if settings.cors_origins and all(
        origin.startswith(("http://localhost", "http://127.0.0.1"))
        for origin in settings.cors_origins
    ):
        raise RuntimeError("Production CORS_ORIGINS must not use only localhost origins")

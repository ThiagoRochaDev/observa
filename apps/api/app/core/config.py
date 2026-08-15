from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[4]  # observa/
DATA_DIR = ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Observa"
    data_dir: Path = DATA_DIR
    database_path: Path | None = None
    # Fernet key for encrypting connector secrets (generated & persisted on first boot)
    secrets_key_file: Path | None = None
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


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    return s

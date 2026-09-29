"""Backend settings. Every value can be overridden through environment / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_name: str = "AltCredit API"
    api_prefix: str = "/api/v1"

    # --- Data ----------------------------------------------------------------
    # product catalog, transactions and ground-truth CSVs are read from machine_learning/data
    data_dir: Path = REPO_ROOT / "machine_learning" / "data"
    # user features live with the backend
    merged_data_path: Path = BACKEND_DIR / "data" / "merged_data.json"

    # --- Embedded database ------------------------------------------------
    database_url: str = f"sqlite:///{BACKEND_DIR / 'altcredit.db'}"
    seed_on_startup: bool = True

    # --- Auth (user id + password checked against the database) ---------------
    pbkdf2_iterations: int = 200_000
    # Password given to seeded synthetic users / lenders. Dev-only default,
    # override in .env for anything shared.
    demo_password: str = "altcredit-demo"

    # --- Bank integration (separate application, see bank_mock/) ------------
    bank_api_url: str = "http://127.0.0.1:8001"
    bank_api_key: str = "dev-only-bank-key"
    bank_timeout_seconds: float = 5.0

    # --- CORS: frontend origins allowed to call the API directly ------------
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

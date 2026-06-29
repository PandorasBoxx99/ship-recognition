"""
Centralized configuration using pydantic-settings.
Reads from .env file and environment variables.
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = parent of backend/
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "ShipRecognition"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 3025

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'schiffs-scraper.db'}"

    # Paths (relative to BASE_DIR, resolved at runtime)
    DOWNLOAD_DIR: str = str(BASE_DIR / "downloads")
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    AUGMENTED_DIR: str = str(BASE_DIR / "augmented")
    MODEL_DIR: str = str(BASE_DIR / "models" / "ship_classifier")
    DATA_DIR: str = str(BASE_DIR / "data")
    LOG_DIR: str = str(BASE_DIR / "logs")

    # ML
    DEFAULT_MODEL_NAME: str = "dima806/10_ship_types_image_detection"
    DEFAULT_MODEL_FALLBACK: str = "google/vit-base-patch16-224-in21k"

    # Embeddings / visual similarity (specific-ship recognition via DINOv2)
    EMBEDDING_MODEL: str = "facebook/dinov2-base"  # dinov2-small for CPU-only setups
    SIMILARITY_THRESHOLD: float = 0.6  # open-set: below this -> "no confident match"
    SIMILARITY_MARGIN: float = 0.05  # top1 - top2 must exceed this to be "confident"

    # VPN — NordVPN SOCKS5 proxy
    VPN_ENABLED: bool = True
    VPN_API_KEY: str = ""  # NordVPN access token (from my.nordaccount.com)
    # SOCKS5 exit country for scraper traffic. NordVPN offers SOCKS5 only in a
    # limited set of countries (Netherlands, Sweden, United States).
    VPN_PROXY_COUNTRY: str = "Netherlands"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3025",
        "http://localhost:5173",
    ]

    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 25

    # Secret (for future auth)
    SECRET_KEY: str = "change_me_in_production"

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        for dir_path in [
            self.DOWNLOAD_DIR,
            self.UPLOAD_DIR,
            self.AUGMENTED_DIR,
            self.MODEL_DIR,
            self.DATA_DIR,
            self.LOG_DIR,
        ]:
            os.makedirs(dir_path, exist_ok=True)


settings = Settings()


def update_env_settings(updates: dict) -> list[str]:
    """Persist key/value updates to the .env file and apply them to live settings.

    Keys are lower-case setting names (e.g. "vpn_enabled"); they are written as
    upper-case .env entries (VPN_ENABLED). None values are skipped. Returns the
    list of applied keys. This makes settings changes take effect in real time
    without a server restart.
    """
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
    else:
        example = BASE_DIR / ".env.example"
        content = example.read_text(encoding="utf-8") if example.exists() else ""

    applied = {k: v for k, v in updates.items() if v is not None}
    for key, value in applied.items():
        env_key = key.upper()
        str_value = str(value).lower() if isinstance(value, bool) else str(value)
        if f"{env_key}=" in content:
            lines = content.split("\n")
            content = "\n".join(
                f"{env_key}={str_value}" if line.startswith(f"{env_key}=") else line
                for line in lines
            )
        else:
            content = content.rstrip() + f"\n{env_key}={str_value}\n"
    env_path.write_text(content, encoding="utf-8")

    # Apply to the live settings object so changes take effect immediately
    for key, value in applied.items():
        attr = key.upper()
        if hasattr(settings, attr):
            object.__setattr__(settings, attr, value)
    return list(applied.keys())

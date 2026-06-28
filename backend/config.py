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

    # VPN
    VPN_ENABLED: bool = True
    VPN_BINARY: str = "nordvpn"
    VPN_PROVIDER: str = "nordvpn"
    VPN_USER: str = ""
    VPN_API_KEY: str = ""
    VPN_DEFAULT_COUNTRY: str = "Germany"
    VPN_AUTO_CONNECT: bool = True
    VPN_ROTATION: str = "manual"  # manual, per_job, every_50, every_100
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

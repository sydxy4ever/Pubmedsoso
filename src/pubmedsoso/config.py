"""Configuration management for Pubmedsoso."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Application configuration with sensible defaults."""

    db_dir: Path = Path("./data")
    export_dir: Path = Path("./data/exports")

    page_size: int = 50
    request_timeout: int = 30
    max_retries: int = 3
    retry_backoff: float = 1.0

    web_host: str = "0.0.0.0"
    web_port: int = 8000

    min_request_interval: float = 1.0

    @classmethod
    def from_env(cls) -> "Config":
        """Create config with environment variable overrides.

        Environment variables use PUBMEDSOSO_ prefix.
        Example: PUBMEDSOSO_SCIHUB_ENABLED=false
        """
        config = cls()
        prefix = "PUBMEDSOSO_"

        env_map: dict[str, type] = {
            "PAGE_SIZE": int,
            "REQUEST_TIMEOUT": int,
            "MAX_RETRIES": int,
            "RETRY_BACKOFF": float,
            "WEB_HOST": str,
            "WEB_PORT": int,
            "MIN_REQUEST_INTERVAL": float,
        }

        for key, cast in env_map.items():
            env_val = os.environ.get(f"{prefix}{key}")
            if env_val is not None:
                setattr(config, key.lower(), cast(env_val))

        for key in ("DB_DIR", "EXPORT_DIR"):
            env_val = os.environ.get(f"{prefix}{key}")
            if env_val is not None:
                setattr(config, key.lower(), Path(env_val))

        return config

    def ensure_dirs(self) -> None:
        """Create all configured directories if they don't exist."""
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)

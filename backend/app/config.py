import os
from dataclasses import dataclass


def get_allowed_origins() -> tuple[str, ...]:
    raw_origins = os.getenv("ALLOWED_ORIGINS") or os.getenv(
        "FLEXIGRID_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    return tuple(
        origin.strip()
        for origin in raw_origins.split(",")
        if origin.strip()
    )


@dataclass(frozen=True)
class Settings:
    app_name: str = "FlexiGrid AI API"
    app_version: str = "1.5.0"

    database_path: str = os.getenv(
        "FLEXIGRID_DB",
        os.path.join(os.path.dirname(__file__), "flexigrid.db"),
    )

    default_event_threshold_kw: float = float(
        os.getenv("FLEXIGRID_EVENT_THRESHOLD_KW", "0.8")
    )

    cors_origins: tuple[str, ...] = get_allowed_origins()


settings = Settings()
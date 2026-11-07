import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass
class Settings:

    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", ""), repr=False
    )
    database_schema: str = "public"
    database_pool_size: int = 10
    _pool: object = field(default=None, init=False, repr=False)
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("PCB_DATA_DIR", ROOT / "data")).resolve()
    )
    model_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("PCB_MODEL_PATH", ROOT / "models/best.pt")
        ).resolve()
    )
    manifest_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("PCB_MODEL_MANIFEST", ROOT / "models/model-manifest.json")
        ).resolve()
    )
    secure_cookies: bool = field(
        default_factory=lambda: (
            os.getenv("PCB_SECURE_COOKIES", "false").lower() == "true"
        )
    )
    allowed_origins: tuple = field(
        default_factory=lambda: tuple(
            os.getenv(
                "PCB_ALLOWED_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000",
            ).split(",")
        )
    )
    image_size: int = field(
        default_factory=lambda: int(os.getenv("PCB_IMAGE_SIZE", "1024"))
    )
    device: str = field(default_factory=lambda: os.getenv("PCB_DEVICE", "cpu"))
    session_seconds: int = 60 * 60 * 24
    max_upload: int = 20 * 1024 * 1024

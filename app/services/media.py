from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"


def cabinet_banner_path() -> Path:
    return ASSETS_DIR / "cabinet_banner.jpg"


def photo_placeholder_path() -> Path:
    return ASSETS_DIR / "photo_placeholder.jpg"

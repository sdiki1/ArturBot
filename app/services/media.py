from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"


def _asset_path(*candidates: str) -> Path:
    for filename in candidates:
        path = ASSETS_DIR / filename
        if path.exists():
            return path
    return ASSETS_DIR / candidates[0]


def cabinet_banner_path() -> Path:
    return _asset_path("cabinet_banner.png", "cabinet_banner.jpg")


def photo_placeholder_path() -> Path:
    return _asset_path("photo_placeholder.png", "photo_placeholder.jpg")

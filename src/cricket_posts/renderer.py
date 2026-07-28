"""Shared paths and browser discovery.

This module used to also render the pre-Studio ``Campaign`` proof-of-concept.
That path is gone; everything here is the small set of constants and helpers the
rest of the package imports.
"""

from __future__ import annotations

import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = PROJECT_ROOT / "templates"
ASSET_DIR = PROJECT_ROOT / "assets"
DEFAULT_CHROME_PATHS = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
)


def find_browser() -> Path:
    for candidate in DEFAULT_CHROME_PATHS:
        if candidate.exists():
            return candidate
    for command in ("chrome", "msedge", "chromium"):
        resolved = shutil.which(command)
        if resolved:
            return Path(resolved)
    raise RuntimeError("Chrome, Edge, or Chromium is required to render PNG files.")

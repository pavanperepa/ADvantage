from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import Campaign, PostBrief


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


def render_html(
    campaign: Campaign,
    post: PostBrief,
    background_path: Path,
    html_path: Path,
    concept_label: str | None = None,
) -> Path:
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(("html", "xml")),
    )
    template = environment.get_template(f"{post.template_id.value}.html")
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(
        template.render(
            academy=campaign.academy_name,
            location=campaign.location,
            post=post,
            background_url=background_path.resolve().as_uri(),
            logo_url=(ASSET_DIR / "mark.svg").resolve().as_uri(),
            concept_label=concept_label,
        ),
        encoding="utf-8",
    )
    return html_path


def screenshot(
    html_path: Path,
    png_path: Path,
    *,
    width: int = 1080,
    height: int = 1350,
) -> Path:
    browser = find_browser()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    profile_dir = PROJECT_ROOT / "output" / "chrome-profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--window-size={width},{height}",
        f"--user-data-dir={profile_dir.resolve()}",
        f"--screenshot={png_path.resolve()}",
        html_path.resolve().as_uri(),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"Browser render failed: {result.stderr.strip()}")
    # On Windows the launcher can return just before the browser subprocess
    # finishes writing the screenshot.
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if png_path.exists() and png_path.stat().st_size > 0:
            return png_path
        time.sleep(0.1)
    if not png_path.exists():
        raise RuntimeError("Browser reported success but did not create the PNG.")
    return png_path


def write_campaign_json(campaign: Campaign, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(campaign.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return path


def render_campaign(
    campaign: Campaign,
    output_dir: Path,
    backgrounds: dict[str, Path],
) -> list[Path]:
    html_dir = PROJECT_ROOT / "output" / "html"
    rendered: list[Path] = []
    write_campaign_json(campaign, output_dir / "campaign.json")
    for post in campaign.posts:
        name = post.template_id.value
        labels = {
            "information": "CONCEPT 01 / INFORMATION",
            "tournament": "CONCEPT 02 / REGISTRATION",
            "services": "CONCEPT 03 / SERVICES",
        }
        html_path = render_html(
            campaign,
            post,
            backgrounds[name],
            html_dir / f"{output_dir.name}-{name}.html",
            labels[name] if output_dir.name == "sample" else None,
        )
        rendered.append(screenshot(html_path, output_dir / f"{name}.png"))
    return rendered

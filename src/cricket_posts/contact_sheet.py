from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .renderer import PROJECT_ROOT, screenshot


def create_contact_sheet(images: list[Path], destination: Path) -> Path:
    environment = Environment(loader=FileSystemLoader(PROJECT_ROOT / "templates"))
    template = environment.get_template("contact-sheet.html")
    html_path = PROJECT_ROOT / "output" / "html" / f"{destination.parent.name}-contact-sheet.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(
        template.render(images=[image.resolve().as_uri() for image in images]),
        encoding="utf-8",
    )

    return screenshot(html_path, destination, width=1500, height=760)

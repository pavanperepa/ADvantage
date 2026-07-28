"""The subject bank: transparent cut-outs, real photographs preferred.

Subjects are a separate layer from the plate precisely so a photograph of an
actual student can take the place of a generated child. Real photography wins on
authenticity, on getting the academy's own community right, and on parents
recognising the kids — so `source: photo` always outranks `source: generated`.

Cut-outs must have an alpha channel. Producing one from a flat photo needs
background removal, which is an optional extra (`uv sync --group photos`); a
pre-cut transparent PNG needs no dependency at all.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

from .renderer import ASSET_DIR

SUBJECT_DIR = ASSET_DIR / "subjects"
MANIFEST = SUBJECT_DIR / "manifest.json"


class SubjectSource(str, Enum):
    PHOTO = "photo"
    GENERATED = "generated"


class SubjectEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str
    source: SubjectSource = SubjectSource.GENERATED
    tags: list[str] = Field(default_factory=list)
    note: str = ""

    def path(self, root: Path = SUBJECT_DIR) -> Path:
        return root / self.file


class SubjectBank(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[SubjectEntry] = Field(default_factory=list)

    @classmethod
    def load(cls, manifest: Path = MANIFEST) -> "SubjectBank":
        if not manifest.exists():
            return cls()
        return cls.model_validate_json(manifest.read_text(encoding="utf-8"))

    def save(self, manifest: Path = MANIFEST) -> Path:
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(self.model_dump_json(indent=2), encoding="utf-8")
        return manifest

    def select(
        self,
        tags: list[str] | None = None,
        *,
        limit: int = 1,
        root: Path = SUBJECT_DIR,
    ) -> list[SubjectEntry]:
        wanted = set(tags or [])

        def rank(entry: SubjectEntry) -> tuple[int, int]:
            # Photographs first, then by how many requested tags they match.
            return (
                0 if entry.source is SubjectSource.PHOTO else 1,
                -len(wanted & set(entry.tags)),
            )

        available = [entry for entry in self.entries if entry.path(root).exists()]
        return sorted(available, key=rank)[:limit]


def has_alpha(path: Path) -> bool:
    with Image.open(path) as image:
        return image.mode in {"RGBA", "LA"} or "transparency" in image.info


def index_subjects(root: Path = SUBJECT_DIR) -> SubjectBank:
    existing = {
        entry.file: entry for entry in SubjectBank.load(root / "manifest.json").entries
    }
    entries = [
        existing.get(path.name, SubjectEntry(file=path.name))
        for path in sorted(root.glob("*.png"))
    ]
    bank = SubjectBank(entries=entries)
    bank.save(root / "manifest.json")
    return bank


def cut_out(source: Path, destination: Path) -> Path:
    """Remove the background from a photograph, producing a transparent PNG.

    Optional: requires `rembg`. Without it, supply a pre-cut PNG instead.
    """
    try:
        from rembg import remove  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError(
            "Background removal needs the optional 'photos' extra: "
            "uv sync --group photos. Alternatively supply a transparent PNG."
        ) from exc
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(remove(source.read_bytes()))
    return destination

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
        only_file: str | None = None,
    ) -> list[SubjectEntry]:
        wanted = set(tags or [])
        if only_file:
            named = [entry for entry in self.entries if entry.file == only_file]
            if not named:
                raise LookupError(f"No subject named {only_file!r} in the bank")
            return named[:limit]

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


#: Salient-object model, the same weights rembg downloads. Running it directly
#: keeps the optional extra to onnxruntime + numpy: rembg itself drags in
#: pymatting and numba, and numba has no build for this Python.
U2NET_MODEL = Path.home() / ".u2net" / "u2net.onnx"
_U2NET_SIZE = (320, 320)
_MEAN = (0.485, 0.456, 0.406)
_STD = (0.229, 0.224, 0.225)

_SESSION: object | None = None


def _session(model: Path = U2NET_MODEL):  # pragma: no cover - optional extra
    """One session per process: loading 176MB of weights per call is wasteful."""
    global _SESSION
    if _SESSION is None:
        try:
            import onnxruntime
        except ImportError as exc:
            raise RuntimeError(
                "Background removal needs the optional 'photos' extra: "
                "uv sync --group photos. Alternatively supply a transparent PNG."
            ) from exc
        if not model.exists():
            raise RuntimeError(f"u2net weights not found at {model}")
        _SESSION = onnxruntime.InferenceSession(
            str(model), providers=["CPUExecutionProvider"]
        )
    return _SESSION


def _saliency(image: Image.Image, model: Path = U2NET_MODEL) -> Image.Image:
    """A soft greyscale mask of the salient subject, at the image's own size."""
    import numpy as np

    session = _session(model)
    sample = np.asarray(
        image.convert("RGB").resize(_U2NET_SIZE, Image.LANCZOS), dtype=np.float32
    )
    peak = sample.max()
    sample = sample / (peak if peak else 1.0)
    sample = (sample - np.array(_MEAN, dtype=np.float32)) / np.array(
        _STD, dtype=np.float32
    )
    batch = sample.transpose(2, 0, 1)[None].astype(np.float32)

    prediction = session.run(None, {session.get_inputs()[0].name: batch})[0][:, 0]
    low, high = prediction.min(), prediction.max()
    prediction = (prediction - low) / (high - low if high > low else 1.0)

    flat = (np.squeeze(prediction) * 255).astype(np.uint8)
    return Image.fromarray(flat, mode="L").resize(image.size, Image.LANCZOS)


def _subject_box(
    mask: Image.Image,
    *,
    threshold: int = 32,
    pad: float = 0.06,
) -> tuple[int, int, int, int]:
    box = mask.point(lambda v: 255 if v > threshold else 0).getbbox()
    if box is None:
        return (0, 0, mask.width, mask.height)
    left, top, right, bottom = box
    margin_x = int((right - left) * pad)
    margin_y = int((bottom - top) * pad)
    return (
        max(0, left - margin_x),
        max(0, top - margin_y),
        min(mask.width, right + margin_x),
        min(mask.height, bottom + margin_y),
    )


def cut_out(
    source: Path,
    destination: Path,
    *,
    model: Path = U2NET_MODEL,
    max_height: int = 2200,
    refine: bool = True,
) -> Path:
    """Remove the background from a photograph, producing a transparent PNG.

    The model only ever sees 320x320, so on a 6000px photo a single pass gives a
    mask whose true resolution is ~20x too coarse and the edges turn to mush.
    Running it a second time on a tight crop of the subject spends that same
    320x320 budget on the child alone, which is where the detail is needed.

    Optional: requires `uv sync --group photos`. A pre-cut transparent PNG needs
    no dependency at all.
    """
    with Image.open(source) as opened:
        photo = opened.convert("RGB")
    if photo.height > max_height:
        photo = photo.resize(
            (round(photo.width * max_height / photo.height), max_height),
            Image.LANCZOS,
        )

    mask = _saliency(photo, model)
    if refine:
        box = _subject_box(mask)
        crop = photo.crop(box)
        if crop.width > 16 and crop.height > 16:
            sharper = mask.copy()
            sharper.paste(_saliency(crop, model), box)
            mask = sharper

    cut = photo.convert("RGBA")
    cut.putalpha(mask)
    cut = cut.crop(_subject_box(mask, pad=0.0) if mask.getbbox() else cut.getbbox())

    destination.parent.mkdir(parents=True, exist_ok=True)
    cut.save(destination)
    return destination

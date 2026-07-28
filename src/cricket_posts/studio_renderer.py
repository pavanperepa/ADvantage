from __future__ import annotations

import atexit
import math
import re
import statistics
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image
from playwright.sync_api import sync_playwright

from .intent_assets import ensure_intent_assets
from .layout_score import score_layout
from .theme import build_theme
from .models import (
    AuditIssue,
    AuditSeverity,
    BrandProfile,
    InkKind,
    InkRect,
    PosterGeometry,
    PosterProject,
    Rect,
    RegionGeometry,
    TextBackdrop,
    ValidationReport,
)
from .renderer import PROJECT_ROOT, TEMPLATE_DIR, find_browser


STUDIO_TEMPLATE_DIR = TEMPLATE_DIR / "studio"
# Family names are intentionally unquoted: these strings are interpolated into a
# <style> block by an autoescaping Jinja environment, which would turn quotes
# into entities and break the declaration. CSS accepts unquoted family names made
# of valid identifiers, which every bundled face is. System faces trail each
# stack so a missing woff2 degrades instead of failing.
FONT_STACKS = {
    "athletic": {
        "display": "Anton, Impact, Haettenschweiler, sans-serif",
        "body": "Archivo Narrow, Arial Narrow, Arial, sans-serif",
    },
    "modern": {
        "display": "Space Grotesk, Bahnschrift Condensed, Arial, sans-serif",
        "body": "Inter, Segoe UI, Aptos, Arial, sans-serif",
    },
    "geometric": {
        "display": "Outfit, Century Gothic, Trebuchet MS, sans-serif",
        "body": "Outfit, Trebuchet MS, Segoe UI, sans-serif",
    },
    "editorial": {
        "display": "Playfair Display, Georgia, Times New Roman, serif",
        "body": "Inter, Segoe UI, Aptos, Arial, sans-serif",
    },
    "impact": {
        "display": "Archivo Black, Impact, Arial Black, sans-serif",
        "body": "Archivo, Segoe UI, Arial, sans-serif",
    },
    "condensed": {
        "display": "Bebas Neue, Impact, Arial Narrow Bold, sans-serif",
        "body": "Archivo Narrow, Arial Narrow, Arial, sans-serif",
    },
    "friendly": {
        "display": "Fraunces, Georgia, Times New Roman, serif",
        "body": "Poppins, Segoe UI, Arial, sans-serif",
    },
    "rounded": {
        "display": "Poppins, Century Gothic, Trebuchet MS, sans-serif",
        "body": "Poppins, Segoe UI, Arial, sans-serif",
    },
}

# Minimum readable contrast, matching the existing CSS-derived audit gate.
CONTRAST_FLOOR = 4.5
# Backdrop luminance spread above which text sits on visibly busy artwork.
BUSY_BACKDROP_STDEV = 0.12
# Glyphs are made transparent for the backdrop pass so the artwork behind them
# can be sampled. visibility:hidden would be wrong: several elements carry both
# the copy hook and their own painted background (.eyebrow-chip, .schedule-strip,
# .price-line), so hiding them would erase the very panel the text sits on and
# report a false contrast failure against the artwork underneath.
BACKDROP_STYLE = (
    "#poster,#poster *,#poster *::before,#poster *::after{"
    "color:transparent !important;"
    "text-shadow:none !important;"
    "-webkit-text-stroke-color:transparent !important}"
)

_SRGB_TO_LINEAR = tuple(
    (channel / 255) / 12.92
    if (channel / 255) <= 0.04045
    else math.pow(((channel / 255) + 0.055) / 1.055, 2.4)
    for channel in range(256)
)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _color_channels(value: str) -> tuple[int, int, int] | None:
    # Note: alpha is deliberately ignored here. This function backs the original
    # CSS-derived contrast check, which cannot see through translucent panels at
    # all. TextBackdrop measurements sample real pixels and supersede it.
    numbers = re.findall(r"[\d.]+", value)
    if len(numbers) < 3:
        return None
    channels = [float(number) for number in numbers[:3]]
    if "color(srgb" in value and all(channel <= 1 for channel in channels):
        channels = [channel * 255 for channel in channels]
    return tuple(round(channel) for channel in channels)


def _relative_luminance(color: tuple[int, int, int]) -> float:
    converted = []
    for channel in color:
        normalized = channel / 255
        converted.append(
            normalized / 12.92
            if normalized <= 0.04045
            else math.pow((normalized + 0.055) / 1.055, 2.4)
        )
    return 0.2126 * converted[0] + 0.7152 * converted[1] + 0.0722 * converted[2]


def _contrast_ratio(foreground: str, background: str) -> float | None:
    foreground_rgb = _color_channels(foreground)
    background_rgb = _color_channels(background)
    if foreground_rgb is None or background_rgb is None:
        return None
    first = _relative_luminance(foreground_rgb)
    second = _relative_luminance(background_rgb)
    lighter = max(first, second)
    darker = min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def _ratio_from_luminance(first: float, second: float) -> float:
    lighter = max(first, second)
    darker = min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def _percentile(samples: list[float], fraction: float) -> float:
    if not samples:
        return 0.0
    index = min(len(samples) - 1, max(0, round(fraction * (len(samples) - 1))))
    return samples[index]


MEASURE_SCRIPT = """
() => {
  const poster = document.querySelector("#poster");
  const posterRect = poster.getBoundingClientRect();

  const audited = [...document.querySelectorAll("[data-audit]")].map(el => {
    const rect = el.getBoundingClientRect();
    return {
      field: el.dataset.field || el.tagName.toLowerCase(),
      left: rect.left,
      top: rect.top,
      right: rect.right,
      bottom: rect.bottom,
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
      scrollHeight: el.scrollHeight,
      clientHeight: el.clientHeight,
    };
  });
  const bodyText = [...document.querySelectorAll("[data-body]")].map(el => {
    const style = getComputedStyle(el);
    const panel = el.closest("[data-panel]");
    const panelStyle = panel ? getComputedStyle(panel) : getComputedStyle(poster);
    return {
      field: el.closest("[data-field]")?.dataset.field || "body text",
      text: el.innerText,
      fontSize: parseFloat(style.fontSize),
      color: style.color,
      background: panelStyle.backgroundColor,
    };
  });
  const logo = document.querySelector("[data-logo]");

  const width = posterRect.width;
  const height = posterRect.height;
  const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
  const toLocal = (rect) => ({
    left: clamp(rect.left - posterRect.left, 0, width),
    top: clamp(rect.top - posterRect.top, 0, height),
    right: clamp(rect.right - posterRect.left, 0, width),
    bottom: clamp(rect.bottom - posterRect.top, 0, height),
  });
  const isVisible = (rect) =>
    rect.right - rect.left > 0.5 && rect.bottom - rect.top > 0.5;
  const areaOf = (rect) => (rect.right - rect.left) * (rect.bottom - rect.top);

  // Ranges are built over text nodes rather than whole elements so the rects are
  // the real glyph footprint. Using selectNodeContents on the element would span
  // inline replaced children too, and sampling an inline .intent-icon as if it
  // were the backdrop behind the copy reports a false contrast failure.
  const glyphRects = (el) => {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const rects = [];
    let node = walker.nextNode();
    while (node) {
      if (node.nodeValue && node.nodeValue.trim()) {
        const range = document.createRange();
        range.selectNodeContents(node);
        for (const rect of range.getClientRects()) {
          const local = toLocal(rect);
          if (isVisible(local)) rects.push(local);
        }
      }
      node = walker.nextNode();
    }
    return rects.slice(0, 32);
  };

  const textLeaves = [...document.querySelectorAll("[data-copy],[data-body]")]
    .filter(el => el.querySelector("[data-copy],[data-body]") === null);
  const leafRects = new Map();
  for (const el of textLeaves) leafRects.set(el, glyphRects(el));

  const regionOf = (el) => el.closest("[data-region]")?.dataset.region || "";
  const fieldOf = (el) => el.closest("[data-field]")?.dataset.field || "";

  const textBoxes = textLeaves.map(el => {
    const style = getComputedStyle(el);
    return {
      region: regionOf(el),
      field: fieldOf(el),
      color: style.color,
      fontSize: parseFloat(style.fontSize),
      box: toLocal(el.getBoundingClientRect()),
      rects: leafRects.get(el),
    };
  }).filter(item => item.rects.length > 0);

  const inkRects = [];
  for (const item of textBoxes) {
    for (const rect of item.rects) {
      inkRects.push({ ...rect, kind: "text" });
    }
  }
  for (const el of document.querySelectorAll("[data-panel]")) {
    const rect = toLocal(el.getBoundingClientRect());
    if (isVisible(rect)) inkRects.push({ ...rect, kind: "panel" });
  }
  for (const el of document.querySelectorAll("img")) {
    if (el.closest("[data-art]")) continue;
    const rect = toLocal(el.getBoundingClientRect());
    if (isVisible(rect)) inkRects.push({ ...rect, kind: "image" });
  }

  // Glyph area only. Icons and photographs are tracked separately as image ink,
  // so this stays a measure of how densely a container is packed with type.
  const inkAreaWithin = (el) => {
    let sum = 0;
    for (const [leaf, rects] of leafRects) {
      if (el === leaf || el.contains(leaf)) {
        sum += rects.reduce((total, rect) => total + areaOf(rect), 0);
      }
    }
    return sum;
  };

  const regionEls = [...document.querySelectorAll("[data-region]")];
  const regions = regionEls.map(el => {
    const parent = el.parentElement?.closest("[data-region]");
    let depth = 0;
    let walker = el.parentElement?.closest("[data-region]");
    while (walker) {
      depth += 1;
      walker = walker.parentElement?.closest("[data-region]");
    }
    return {
      regionId: el.dataset.region,
      parentId: parent ? parent.dataset.region : "",
      depth,
      box: toLocal(el.getBoundingClientRect()),
      inkArea: inkAreaWithin(el),
      textLength: (el.innerText || "").trim().length,
      fontSize: parseFloat(getComputedStyle(el).fontSize),
      isPanel: el.hasAttribute("data-panel"),
      isArt: el.hasAttribute("data-art"),
      isLeaf: el.querySelector("[data-region]") === null,
    };
  });

  const census = new Map();
  for (const item of textBoxes) {
    const size = Math.round(item.fontSize * 10) / 10;
    const ink = item.rects.reduce((a, r) => a + areaOf(r), 0);
    census.set(size, (census.get(size) || 0) + ink);
  }
  const fontCensus = [...census.entries()].sort((a, b) => b[0] - a[0]);

  const artEl = document.querySelector("[data-art]");

  return {
    poster: {
      width: posterRect.width,
      height: posterRect.height,
      scrollWidth: poster.scrollWidth,
      scrollHeight: poster.scrollHeight,
    },
    page: {
      scrollWidth: document.documentElement.scrollWidth,
      scrollHeight: document.documentElement.scrollHeight,
    },
    visibleText: poster.innerText,
    audited,
    bodyText,
    logo: logo ? {
      present: true,
      naturalWidth: logo.naturalWidth,
      naturalHeight: logo.naturalHeight,
    } : { present: false },
    geometry: {
      regions,
      inkRects,
      textBoxes,
      fontCensus,
      art: artEl ? toLocal(artEl.getBoundingClientRect()) : null,
    },
  };
}
"""


@dataclass(slots=True)
class RenderJob:
    html_path: Path
    png_path: Path
    project: PosterProject
    brand: BrandProfile


class _BrowserSession:
    """One Playwright driver plus browser, owned by a single thread.

    Playwright's sync objects are bound to the thread that created them, so a
    process-wide shared browser would break under the FastAPI threadpool.
    """

    def __init__(self) -> None:
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.launch(
            executable_path=str(find_browser()),
            headless=True,
            args=["--disable-gpu", "--hide-scrollbars"],
        )

    def close(self) -> None:
        try:
            self.browser.close()
        finally:
            self._playwright.stop()


_SESSIONS: dict[int, _BrowserSession] = {}
_SESSIONS_GUARD = threading.Lock()


def _close_all_sessions() -> None:
    # Best effort. Sessions belonging to other threads usually refuse to close
    # from here, but the driver subprocess exits with the interpreter anyway.
    with _SESSIONS_GUARD:
        sessions = list(_SESSIONS.items())
        _SESSIONS.clear()
    for _, session in sessions:
        try:
            session.close()
        except Exception:
            pass


atexit.register(_close_all_sessions)


class PlaywrightRenderer:
    def __init__(self, template_dir: Path = STUDIO_TEMPLATE_DIR) -> None:
        self.template_dir = template_dir
        self.environment = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(("html", "xml")),
        )

    def _session(self) -> _BrowserSession:
        key = threading.get_ident()
        with _SESSIONS_GUARD:
            session = _SESSIONS.get(key)
            if session is None:
                session = _BrowserSession()
                _SESSIONS[key] = session
            return session

    def close(self) -> None:
        """Dispose this thread's browser session, if it started one."""
        key = threading.get_ident()
        with _SESSIONS_GUARD:
            session = _SESSIONS.pop(key, None)
        if session is not None:
            session.close()

    def write_html(
        self,
        project: PosterProject,
        brand: BrandProfile,
        artwork_path: Path,
        destination: Path,
    ) -> Path:
        if project.design is None:
            raise ValueError("Project has no DesignSpec.")
        logo_path = Path(brand.logo_path) if brand.logo_path else None
        if logo_path and not logo_path.is_absolute():
            logo_path = PROJECT_ROOT / logo_path
        if logo_path and not logo_path.exists():
            logo_path = None
        intent_icons = ensure_intent_assets(
            destination.parent / "intent-icons",
            project.design,
        )
        font_stack = FONT_STACKS[project.design.font_preset.value]
        # Older projects were stored before theming existed, so resolve on demand.
        theme = project.design.theme or build_theme(
            project.design.style_intent,
            project.design.palette,
            project.design.color_mode,
            project.design.font_preset,
        )
        html = self.environment.get_template("poster.html").render(
            project=project,
            brand=brand,
            content=project.content,
            design=project.design,
            theme=theme,
            artwork_url=artwork_path.resolve().as_uri(),
            intent_icons=intent_icons,
            display_font=font_stack["display"],
            body_font=font_stack["body"],
            logo_url=logo_path.resolve().as_uri() if logo_path else None,
            stylesheet_url=(self.template_dir / "studio.css").resolve().as_uri(),
            fonts_url=(self.template_dir / "fonts.css").resolve().as_uri(),
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(html, encoding="utf-8")
        return destination

    def _capture(self, page: Any, job: RenderJob) -> ValidationReport:
        if job.project.design is None:
            raise ValueError("Project has no DesignSpec.")
        design = job.project.design
        clip = {"x": 0, "y": 0, "width": design.width, "height": design.height}
        job.png_path.parent.mkdir(parents=True, exist_ok=True)
        page.goto(job.html_path.resolve().as_uri(), wait_until="networkidle")
        # Bundled woff2 faces use font-display: block, so screenshotting before
        # they resolve would capture fallback metrics and silently change every
        # measurement downstream.
        page.evaluate("() => document.fonts.ready.then(() => true)")
        page.screenshot(path=str(job.png_path), clip=clip)
        metrics: dict[str, Any] = page.evaluate(MEASURE_SCRIPT)

        # Second pass with every text node hidden. What remains is exactly what
        # sits behind the copy, which is the only honest contrast reference.
        backdrop_path = job.png_path.with_name(f"{job.png_path.stem}-backdrop.png")
        page.add_style_tag(content=BACKDROP_STYLE)
        page.screenshot(path=str(backdrop_path), clip=clip)
        backdrops = measure_backdrops(backdrop_path, metrics)
        return audit_render(job.png_path, job.project, job.brand, metrics, backdrops)

    def render_and_measure(
        self,
        html_path: Path,
        png_path: Path,
        project: PosterProject,
        brand: BrandProfile,
    ) -> ValidationReport:
        if project.design is None:
            raise ValueError("Project has no DesignSpec.")
        session = self._session()
        page = session.browser.new_page(
            viewport={"width": project.design.width, "height": project.design.height},
            device_scale_factor=1,
        )
        try:
            return self._capture(
                page,
                RenderJob(html_path, png_path, project, brand),
            )
        finally:
            page.close()

    def render_batch(self, jobs: list[RenderJob]) -> list[ValidationReport]:
        """Render many candidates through one browser and one reused page.

        The per-render browser launch dominates single-poster cost, so batching
        is what makes wide layout search affordable.
        """
        if not jobs:
            return []
        first = jobs[0].project.design
        if first is None:
            raise ValueError("Project has no DesignSpec.")
        session = self._session()
        page = session.browser.new_page(
            viewport={"width": first.width, "height": first.height},
            device_scale_factor=1,
        )
        reports: list[ValidationReport] = []
        try:
            for job in jobs:
                design = job.project.design
                if design is None:
                    raise ValueError("Project has no DesignSpec.")
                if (design.width, design.height) != (first.width, first.height):
                    page.set_viewport_size(
                        {"width": design.width, "height": design.height}
                    )
                    first = design
                reports.append(self._capture(page, job))
        finally:
            page.close()
        return reports


def _luminance_samples(
    image: Image.Image,
    rect: dict[str, float],
    max_side: int = 96,
) -> list[float]:
    left = max(0, int(math.floor(rect["left"])))
    top = max(0, int(math.floor(rect["top"])))
    right = min(image.width, int(math.ceil(rect["right"])))
    bottom = min(image.height, int(math.ceil(rect["bottom"])))
    if right - left < 1 or bottom - top < 1:
        return []
    crop = image.crop((left, top, right, bottom))
    if crop.width > max_side or crop.height > max_side:
        crop = crop.resize(
            (min(crop.width, max_side), min(crop.height, max_side)),
            Image.Resampling.BOX,
        )
    if crop.mode != "RGB":
        crop = crop.convert("RGB")
    # tobytes avoids the deprecated getdata iterator and is faster besides.
    data = crop.tobytes()
    return [
        0.2126 * _SRGB_TO_LINEAR[data[offset]]
        + 0.7152 * _SRGB_TO_LINEAR[data[offset + 1]]
        + 0.0722 * _SRGB_TO_LINEAR[data[offset + 2]]
        for offset in range(0, len(data), 3)
    ]


def measure_backdrops(
    backdrop_path: Path,
    metrics: dict[str, Any],
) -> list[TextBackdrop]:
    text_boxes = metrics.get("geometry", {}).get("textBoxes", [])
    if not text_boxes:
        return []
    results: list[TextBackdrop] = []
    with Image.open(backdrop_path) as image:
        image.load()
        for item in text_boxes:
            samples: list[float] = []
            for rect in item.get("rects", []):
                samples.extend(_luminance_samples(image, rect))
            if not samples:
                continue
            samples.sort()
            text_rgb = _color_channels(item.get("color", ""))
            if text_rgb is None:
                continue
            text_luminance = _relative_luminance(text_rgb)
            p10 = _percentile(samples, 0.10)
            p50 = _percentile(samples, 0.50)
            p90 = _percentile(samples, 0.90)
            results.append(
                TextBackdrop(
                    region_id=item.get("region", ""),
                    field=item.get("field", ""),
                    text_color=item.get("color", ""),
                    font_size=item.get("fontSize", 0.0) or 0.0,
                    contrast_worst=min(
                        _ratio_from_luminance(text_luminance, p10),
                        _ratio_from_luminance(text_luminance, p90),
                    ),
                    contrast_median=_ratio_from_luminance(text_luminance, p50),
                    luminance_p10=p10,
                    luminance_p50=p50,
                    luminance_p90=p90,
                    luminance_stdev=(
                        statistics.pstdev(samples) if len(samples) > 1 else 0.0
                    ),
                    sample_count=len(samples),
                )
            )
    return results


def build_geometry(
    project: PosterProject,
    metrics: dict[str, Any],
    backdrops: list[TextBackdrop],
) -> PosterGeometry:
    if project.design is None:
        raise ValueError("Project has no DesignSpec.")
    payload = metrics.get("geometry", {})
    regions = [
        RegionGeometry(
            region_id=item["regionId"],
            parent_id=item.get("parentId", ""),
            depth=item.get("depth", 0),
            box=Rect(**item["box"]),
            ink_area=item.get("inkArea", 0.0),
            text_length=item.get("textLength", 0),
            font_size=item.get("fontSize", 0.0) or 0.0,
            is_panel=bool(item.get("isPanel")),
            is_art=bool(item.get("isArt")),
            is_leaf=bool(item.get("isLeaf")),
        )
        for item in payload.get("regions", [])
    ]
    ink_rects = [
        InkRect(
            left=item["left"],
            top=item["top"],
            right=item["right"],
            bottom=item["bottom"],
            kind=InkKind(item["kind"]),
        )
        for item in payload.get("inkRects", [])
    ]
    art = payload.get("art")
    return PosterGeometry(
        width=project.design.width,
        height=project.design.height,
        composition=project.design.composition,
        visual_treatment=project.design.visual_treatment,
        safe_margin_px=project.design.safe_margin_px,
        regions=regions,
        ink_rects=ink_rects,
        text_backdrops=backdrops,
        font_census=[
            (float(size), float(area)) for size, area in payload.get("fontCensus", [])
        ],
        art=Rect(**art) if art else None,
    )


def audit_render(
    png_path: Path,
    project: PosterProject,
    brand: BrandProfile,
    metrics: dict[str, Any],
    backdrops: list[TextBackdrop] | None = None,
) -> ValidationReport:
    if project.design is None:
        raise ValueError("Project has no DesignSpec.")
    backdrops = backdrops or []
    issues: list[AuditIssue] = []
    checks: dict[str, bool] = {}
    visible = _normalize(metrics["visibleText"])
    copy_matches = {
        value: _normalize(value) in visible for value in project.content.protected_copy
    }
    checks["protected_copy"] = all(copy_matches.values())
    for value, matches in copy_matches.items():
        if not matches:
            issues.append(
                AuditIssue(
                    code="missing_protected_copy",
                    severity=AuditSeverity.ERROR,
                    message="Protected copy is missing from the rendered poster.",
                    value=value,
                )
            )

    poster_metrics = metrics["poster"]
    checks["document_size"] = (
        round(poster_metrics["width"]) == project.design.width
        and round(poster_metrics["height"]) == project.design.height
        and metrics["page"]["scrollWidth"] <= project.design.width
        and metrics["page"]["scrollHeight"] <= project.design.height
    )
    if not checks["document_size"]:
        issues.append(
            AuditIssue(
                code="document_overflow",
                severity=AuditSeverity.ERROR,
                message="The HTML document exceeds the poster canvas.",
            )
        )

    overflow_fields: list[str] = []
    overflow_details: list[dict[str, Any]] = []
    safe_margin = project.design.safe_margin_px
    scroll_tolerance = 3
    for item in metrics["audited"]:
        reasons = []
        if item["scrollWidth"] > item["clientWidth"] + scroll_tolerance:
            reasons.append("horizontal content overflow")
        if item["scrollHeight"] > item["clientHeight"] + scroll_tolerance:
            reasons.append("vertical content overflow")
        if item["left"] < safe_margin - 1:
            reasons.append("left safe-margin violation")
        if item["top"] < safe_margin - 1:
            reasons.append("top safe-margin violation")
        if item["right"] > project.design.width - safe_margin + 1:
            reasons.append("right safe-margin violation")
        if item["bottom"] > project.design.height - safe_margin + 1:
            reasons.append("bottom safe-margin violation")
        clipped = bool(reasons)
        if clipped:
            overflow_fields.append(item["field"])
            overflow_details.append(
                {
                    "field": item["field"],
                    "reasons": reasons,
                    "bounds": {
                        key: item[key]
                        for key in ("left", "top", "right", "bottom")
                    },
                    "content_size": [
                        item["scrollWidth"],
                        item["scrollHeight"],
                    ],
                    "box_size": [
                        item["clientWidth"],
                        item["clientHeight"],
                    ],
                }
            )
    checks["safe_margins_and_overflow"] = not overflow_fields
    for field in dict.fromkeys(overflow_fields):
        issues.append(
            AuditIssue(
                code="content_overflow",
                severity=AuditSeverity.ERROR,
                message=(
                    "Content is clipped or outside the safe area. Shorten or omit copy in "
                    f"“{field}” and rerender."
                ),
                field=field,
            )
        )

    undersized = [
        item
        for item in metrics["bodyText"]
        if item["fontSize"] + 0.1 < project.design.min_body_px
    ]
    checks["minimum_body_size"] = not undersized
    for item in undersized[:8]:
        issues.append(
            AuditIssue(
                code="body_text_too_small",
                severity=AuditSeverity.ERROR,
                message=(
                    f"Body text is {item['fontSize']:.1f}px; minimum is "
                    f"{project.design.min_body_px}px."
                ),
                field=item["field"],
                value=item["text"],
            )
        )

    low_contrast = []
    contrast_ratios: list[float] = []
    for item in metrics["bodyText"]:
        ratio = _contrast_ratio(item["color"], item["background"])
        if ratio is not None:
            contrast_ratios.append(ratio)
            if ratio < CONTRAST_FLOOR:
                low_contrast.append((item, ratio))
    checks["contrast"] = not low_contrast
    for item, ratio in low_contrast[:8]:
        issues.append(
            AuditIssue(
                code="low_contrast",
                severity=AuditSeverity.ERROR,
                message=f"Body-text contrast is {ratio:.2f}:1; minimum is 4.5:1.",
                field=item["field"],
                value=item["text"],
            )
        )

    # Pixel-measured contrast. Reported only for now: it supersedes the CSS check
    # above but the thresholds have not been calibrated across every fixture yet.
    weak_backdrops = [
        item for item in backdrops if item.contrast_worst < CONTRAST_FLOOR
    ]
    checks["contrast_measured"] = not weak_backdrops
    for item in weak_backdrops[:8]:
        issues.append(
            AuditIssue(
                code="low_contrast_measured",
                severity=AuditSeverity.WARNING,
                message=(
                    f"Measured contrast against the real backdrop is "
                    f"{item.contrast_worst:.2f}:1; minimum is {CONTRAST_FLOOR}:1."
                ),
                field=item.field or item.region_id,
            )
        )
    busy_backdrops = [
        item for item in backdrops if item.luminance_stdev > BUSY_BACKDROP_STDEV
    ]
    checks["backdrop_calm"] = not busy_backdrops
    for item in busy_backdrops[:8]:
        issues.append(
            AuditIssue(
                code="busy_backdrop",
                severity=AuditSeverity.WARNING,
                message=(
                    "Text sits on visibly busy artwork (backdrop luminance spread "
                    f"{item.luminance_stdev:.3f})."
                ),
                field=item.field or item.region_id,
            )
        )

    logo = metrics["logo"]
    checks["logo"] = not brand.logo_path or (
        logo.get("present")
        and logo.get("naturalWidth", 0) > 0
        and logo.get("naturalHeight", 0) > 0
    )
    if not checks["logo"]:
        issues.append(
            AuditIssue(
                code="logo_missing",
                severity=AuditSeverity.ERROR,
                message="The configured brand logo did not load.",
            )
        )

    with Image.open(png_path) as image:
        png_dimensions = image.size
    checks["png_dimensions"] = png_dimensions == (
        project.design.width,
        project.design.height,
    )
    if not checks["png_dimensions"]:
        issues.append(
            AuditIssue(
                code="wrong_png_dimensions",
                severity=AuditSeverity.ERROR,
                message=(
                    f"PNG is {png_dimensions[0]}x{png_dimensions[1]}; expected "
                    f"{project.design.width}x{project.design.height}."
                ),
            )
        )

    geometry = build_geometry(project, metrics, backdrops)
    valid = not any(issue.severity == AuditSeverity.ERROR for issue in issues)
    return ValidationReport(
        valid=valid,
        checks=checks,
        issues=issues,
        measured={
            "png_dimensions": list(png_dimensions),
            "minimum_body_px": min(
                (item["fontSize"] for item in metrics["bodyText"]),
                default=None,
            ),
            "minimum_contrast_ratio": min(contrast_ratios, default=None),
            "minimum_contrast_measured": min(
                (item.contrast_worst for item in backdrops),
                default=None,
            ),
            "contrast_pixel": [
                {
                    "region": item.region_id,
                    "field": item.field,
                    "worst": round(item.contrast_worst, 2),
                    "median": round(item.contrast_median, 2),
                }
                for item in backdrops
            ],
            "backdrop_variance": {
                item.region_id: round(item.luminance_stdev, 4) for item in backdrops
            },
            "overflow_fields": list(dict.fromkeys(overflow_fields)),
            "overflow_details": overflow_details,
        },
        protected_copy_matches=copy_matches,
        geometry=geometry,
        score=score_layout(geometry),
    )

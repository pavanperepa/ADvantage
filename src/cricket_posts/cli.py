from __future__ import annotations

import argparse
import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .archetypes import ArchetypeId
from .models import (
    AuditSeverity,
    BrandProfile,
    ColorMode,
    FontPreset,
    GenerationMode,
    StyleIntent,
    parse_editable_content,
)
from .renderer import PROJECT_ROOT, TEMPLATE_DIR
from .studio import PosterStudio


def run_serve(host: str, port: int, reload: bool) -> None:
    import uvicorn

    if reload:
        uvicorn.run(
            "cricket_posts.web:app",
            host=host,
            port=port,
            reload=True,
        )
        return
    from .web import create_app

    uvicorn.run(create_app(), host=host, port=port)


def run_generate(
    input_path: Path,
    *,
    offline: bool,
    critic: bool,
    color_mode: ColorMode,
    font_preset: FontPreset | None,
    style_intent: StyleIntent | None = None,
) -> None:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    studio = PosterStudio()
    brand_payload = payload.get("brand") if isinstance(payload, dict) else None
    content_payload = payload.get("content", payload) if isinstance(payload, dict) else payload
    if brand_payload:
        brand = studio.save_brand(BrandProfile.model_validate(brand_payload))
    else:
        brand = studio.ensure_default_brand()
    content = parse_editable_content(content_payload)
    project = studio.create_from_content(
        content,
        brand.id,
        source_text=input_path.read_text(encoding="utf-8"),
        use_ai_planner=not offline,
    )
    project = studio.generate(
        project.id,
        use_ideogram=not offline,
        use_critic=critic and not offline,
        render_mode=GenerationMode.HYBRID,
        color_mode=color_mode,
        font_preset=font_preset,
        style_intent=style_intent,
    )
    print(f"Project: {project.id}")
    print(f"Status: {project.status.value}")
    if project.poster_path:
        print(f"Poster: {project.poster_path}")
    if project.error:
        print(f"Message: {project.error}")


def _score_fixture(
    studio: PosterStudio,
    default_brand_id: str,
    fixture_path: Path,
    output_dir: Path,
    style_intent: StyleIntent | None = None,
    color_mode: ColorMode = ColorMode.DARK,
) -> dict[str, Any]:
    label = fixture_path.stem
    if style_intent is not None:
        label = f"{label} · {style_intent.value}"
    row: dict[str, Any] = {
        "fixture": label,
        "intent": style_intent.value if style_intent else "-",
        "font": "-",
        "total": None,
        "valid": False,
        "metrics": [],
        "warnings": [],
        "error": None,
        "image": None,
        "family": "-",
        "composition": "-",
        "treatment": "-",
        "density": "-",
        "contrast_css": "-",
        "contrast_px": "-",
    }
    try:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        brand_payload = payload.get("brand") if isinstance(payload, dict) else None
        content_payload = (
            payload.get("content", payload) if isinstance(payload, dict) else payload
        )
        brand_id = default_brand_id
        if brand_payload:
            brand_id = studio.save_brand(
                BrandProfile.model_validate(brand_payload)
            ).id
        content = parse_editable_content(content_payload)
        project = studio.create_from_content(content, brand_id, use_ai_planner=False)
        project = studio.generate(
            project.id,
            use_ideogram=False,
            style_intent=style_intent,
            color_mode=color_mode,
        )
    except Exception as exc:  # a broken fixture must not abort the sweep
        row["error"] = f"{type(exc).__name__}: {exc}"
        return row

    if project.design is not None:
        row["family"] = project.design.family.value
        row["composition"] = project.design.composition.value
        row["treatment"] = project.design.visual_treatment.value
        row["density"] = project.design.density.value
        row["intent"] = project.design.style_intent.value
        row["font"] = project.design.font_preset.value
    if project.poster_path and Path(project.poster_path).exists():
        suffix = f"-{style_intent.value}" if style_intent else ""
        image_name = f"{fixture_path.stem}{suffix}-{color_mode.value}.png"
        shutil.copyfile(project.poster_path, output_dir / image_name)
        row["image"] = image_name
    audit = project.audit
    if audit is None:
        row["error"] = project.error or "No audit was produced."
        return row
    row["valid"] = audit.valid
    css_ratio = audit.measured.get("minimum_contrast_ratio")
    px_ratio = audit.measured.get("minimum_contrast_measured")
    row["contrast_css"] = f"{css_ratio:.2f}:1" if css_ratio else "-"
    row["contrast_px"] = f"{px_ratio:.2f}:1" if px_ratio else "-"
    row["warnings"] = [
        f"{issue.code}: {issue.message}"
        for issue in audit.issues
        if issue.severity == AuditSeverity.WARNING
    ][:6]
    if not audit.valid:
        row["error"] = project.error
    if audit.score is not None:
        row["total"] = audit.score.total
        row["metrics"] = [metric.model_dump(mode="json") for metric in audit.score.metrics]
    return row


def run_score(
    fixture_dir: Path | None,
    output_dir: Path | None,
    intents: list[StyleIntent] | None = None,
    color_mode: ColorMode = ColorMode.DARK,
) -> None:
    fixture_dir = fixture_dir or PROJECT_ROOT / "fixtures"
    output_dir = output_dir or PROJECT_ROOT / "output" / "calibration"
    output_dir.mkdir(parents=True, exist_ok=True)
    fixtures = sorted(fixture_dir.glob("*.json"))
    if not fixtures:
        raise ValueError(f"No fixtures found in {fixture_dir}")

    # Start clean so a sweep reflects only this run. Without this the database
    # accumulates every earlier run's projects and any analysis over it silently
    # mixes stale geometry with current geometry.
    shutil.rmtree(output_dir / "projects", ignore_errors=True)
    for stale in output_dir.glob("calibration.db*"):
        stale.unlink()

    studio = PosterStudio(
        database_path=output_dir / "calibration.db",
        output_root=output_dir / "projects",
    )
    # Resolved once: saving a fixture's own brand would otherwise become the
    # "default" for every fixture rendered after it.
    default_brand_id = studio.ensure_default_brand().id

    started = time.monotonic()
    if intents:
        rows = [
            _score_fixture(
                studio, default_brand_id, path, output_dir, intent, color_mode
            )
            for path in fixtures
            for intent in intents
        ]
    else:
        rows = [
            _score_fixture(
                studio, default_brand_id, path, output_dir, None, color_mode
            )
            for path in fixtures
        ]
    elapsed = time.monotonic() - started
    rows.sort(key=lambda row: (row["total"] is not None, row["total"] or 0.0))

    (output_dir / "scores.json").write_text(
        json.dumps(rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(("html", "xml")),
    )
    sheet = output_dir / "index.html"
    sheet.write_text(
        environment.get_template("calibration.html").render(
            rows=rows,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        ),
        encoding="utf-8",
    )

    invalid = [row for row in rows if not row["valid"]]
    print(f"Scored {len(rows)} posters in {elapsed:.1f}s\n")
    print(f"{'score':>7}  {'valid':>5}  {'font':>10}  fixture")
    for row in rows:
        total = f"{row['total']:.3f}" if row["total"] is not None else "  -  "
        print(
            f"{total:>7}  {str(row['valid']):>5}  {row['font']:>10}  {row['fixture']}"
        )
    if invalid:
        print(f"\n{len(invalid)} FAILED the audit:")
        for row in invalid:
            print(f"  {row['fixture']}: {row['error']}")
    print(f"\nContact sheet: {sheet}")
    print(f"Raw scores:    {output_dir / 'scores.json'}")


def run_compose(
    input_path: Path,
    *,
    intent: StyleIntent,
    color_mode: ColorMode,
    archetype: str | None,
    logo: Path | None,
    output: Path | None,
    plate: str | None = None,
    subject: str | None = None,
    bullets: str = "auto",
) -> None:
    subjects = [name.strip() for name in (subject or "").split(",") if name.strip()]
    from .pipeline import PosterComposer

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    brand = (
        BrandProfile.model_validate(payload["brand"])
        if isinstance(payload, dict) and "brand" in payload
        else BrandProfile(name="Cricket Academy")
    )
    content = parse_editable_content(
        payload.get("content", payload) if isinstance(payload, dict) else payload
    )
    destination = output or (
        PROJECT_ROOT / "output" / "compose" / f"{input_path.stem}-{intent.value}.png"
    )

    composer = PosterComposer()
    try:
        result = composer.compose(
            content,
            brand,
            destination,
            intent=intent,
            color_mode=color_mode,
            archetype_id=ArchetypeId(archetype) if archetype else None,
            logo_path=logo,
            plate_file=plate,
            subject_files=subjects or None,
            bullets_variant=bullets,
        )
    finally:
        composer.renderer.close()

    print(f"Poster    : {result.poster}")
    print(f"Archetype : {result.archetype.id.value}   Plate: {result.plate.path.name}")
    print(
        f"Zone      : {result.zone.width:.0f}x{result.zone.height:.0f} "
        f"at ({result.zone.left:.0f},{result.zone.top:.0f})"
    )
    print(
        f"Fit       : fill {result.fit.fill:.1%}, {result.fit.iterations} moves, "
        f"{'fits' if result.fit.fits else 'DOES NOT FIT'}"
    )
    if result.fit.history:
        print(f"Moves     : {' -> '.join(result.fit.history)}")
    if result.missing_copy:
        print(f"MISSING COPY ({len(result.missing_copy)}):")
        for value in result.missing_copy:
            print(f"  {value!r}")
    else:
        print("Copy      : every value renders verbatim")
    if result.clipped_copy:
        print(f"CLIPPED ({len(result.clipped_copy)}) — cropped or off-canvas:")
        for value in result.clipped_copy:
            print(f"  {value!r}")


def run_bank_index(kind: str) -> None:
    if kind == "plates":
        from .plates import index_plates

        bank = index_plates()
        print(f"Indexed {len(bank.entries)} plate(s)")
    else:
        from .subjects import index_subjects

        bank = index_subjects()
        print(f"Indexed {len(bank.entries)} subject(s)")


def run_cutout(source: Path, tags: str, limit: int | None) -> None:
    from .subjects import SUBJECT_DIR, SubjectBank, SubjectEntry, SubjectSource, cut_out

    photos = (
        sorted(p for p in source.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
        if source.is_dir()
        else [source]
    )
    if limit:
        photos = photos[:limit]

    wanted = [tag.strip() for tag in tags.split(",") if tag.strip()]
    bank = SubjectBank.load()
    existing = {entry.file: entry for entry in bank.entries}

    for photo in photos:
        destination = SUBJECT_DIR / f"{photo.stem}.png"
        cut_out(photo, destination)
        existing[destination.name] = SubjectEntry(
            file=destination.name,
            source=SubjectSource.PHOTO,
            tags=wanted,
            note=f"Cut from {photo.name}",
        )
        print(f"cut {photo.name} -> {destination.name}")

    SubjectBank(entries=list(existing.values())).save()
    print(f"Subject bank: {len(existing)} entr(ies)")


def run_variants(input_path: Path, count: int, logo: Path | None, output: Path | None) -> None:
    from PIL import Image, ImageDraw

    from .pipeline import PosterComposer

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    brand = (
        BrandProfile.model_validate(payload["brand"])
        if isinstance(payload, dict) and "brand" in payload
        else BrandProfile(name="Cricket Academy")
    )
    content = parse_editable_content(
        payload.get("content", payload) if isinstance(payload, dict) else payload
    )
    out_dir = output or (PROJECT_ROOT / "output" / "variants" / input_path.stem)
    out_dir.mkdir(parents=True, exist_ok=True)

    composer = PosterComposer()
    try:
        results = composer.compose_variants(
            content, brand, out_dir, count=count, logo_path=logo
        )
    finally:
        composer.renderer.close()

    if not results:
        print("No variants produced. Is the plate bank empty?")
        return

    for index, (spec, result) in enumerate(results, 1):
        flags = []
        if result.missing_copy:
            flags.append(f"MISSING {len(result.missing_copy)}")
        if result.clipped_copy:
            flags.append(f"CLIPPED {len(result.clipped_copy)}")
        print(
            f"{index:2}. {spec.plate_file:<30} {spec.intent.value:<20} "
            f"{spec.color_mode.value:<6} {spec.bullets:<8} "
            f"fill {result.fit.fill:.0%} {' '.join(flags)}"
        )

    # One sheet so the whole set can be judged at a glance, which is the entire
    # point of offering options rather than one answer.
    columns = min(3, len(results))
    rows = (len(results) + columns - 1) // columns
    cell = 520
    sheet = Image.new("RGB", (columns * cell, rows * (cell + 26)), "#111318")
    painter = ImageDraw.Draw(sheet)
    for index, (spec, result) in enumerate(results):
        with Image.open(result.poster) as poster:
            thumb = poster.convert("RGB")
        thumb.thumbnail((cell - 16, cell - 16))
        x, y = (index % columns) * cell, (index // columns) * (cell + 26)
        sheet.paste(thumb, (x + (cell - thumb.width) // 2, y + 8))
        painter.text(
            (x + 10, y + cell + 6),
            f"{index + 1}. {spec.intent.value} / {spec.color_mode.value} / {spec.bullets}",
            fill="#E8ECF4",
        )
    sheet_path = out_dir / "contact-sheet.png"
    sheet.save(sheet_path)
    print(f"\nSheet     : {sheet_path}")


def run_harvest(source: Path, name: str | None, max_passes: int, force: bool) -> None:
    from PIL import Image

    from .layerize import harvest
    from .layouts import LAYOUT_DIR, LayoutBank, template_from_blocks

    load_dotenv(PROJECT_ROOT / ".env")
    label = name or source.stem
    result = harvest(source, max_passes=max_passes)

    print(f"Passes    : {result.passes}")
    print(f"Blocks    : {len(result.blocks)}")
    for block in result.blocks:
        print(
            f"  {block.role:<11} ({block.x:.0f},{block.y:.0f}) "
            f"{block.width:.0f}x{block.height:.0f} {block.font_size:.0f}px "
            f"{block.color} {block.text!r}"
            + (f"   <- missed until pass {block.found_on_pass}" if block.found_on_pass > 1 else "")
        )

    if result.residue:
        # The whole reason for the gate: a string we did not write, baked into
        # the plate, would sit under our copy and never be audited.
        print(f"\nREJECTED — text still on the plate after {result.passes} passes:")
        for value in result.residue:
            print(f"  {value!r}")
        if not force:
            print("Nothing banked. Re-generate the source, or raise --max-passes.")
            return
        print("Banking anyway because --force was given.")

    LAYOUT_DIR.mkdir(parents=True, exist_ok=True)
    plate_file = f"{label}.png"
    (LAYOUT_DIR / plate_file).write_bytes(result.base_image)
    with Image.open(LAYOUT_DIR / plate_file) as plate:
        width, height = plate.size

    template = template_from_blocks(
        result.blocks,
        name=label,
        plate_file=plate_file,
        width=width,
        height=height,
        note=f"Harvested from {source.name} in {result.passes} pass(es).",
    )
    LayoutBank.load().add(template).save()

    print(f"\nPlate     : {LAYOUT_DIR / plate_file} ({width}x{height})")
    print(f"Template  : {label} — {len(template.slots)} slot(s)")
    for role, box in template.bands():
        print(
            f"  {role.value:<10} ({box.left:.0f},{box.top:.0f}) "
            f"{box.width:.0f}x{box.height:.0f}"
        )
    suspect = template.suspect_slots()
    if suspect:
        print(
            f"\nReview {len(suspect)} slot(s) the detector missed first time — "
            "usually fragments of garbled type, not real components:"
        )
        for slot in suspect:
            print(
                f"  {slot.role.value} ({slot.box.left:.0f},{slot.box.top:.0f}) "
                f"{slot.box.width:.0f}x{slot.box.height:.0f}"
            )


def run_validate(project_id: str) -> None:
    project = PosterStudio().validate(project_id)
    print(f"Project: {project.id}")
    print(f"Valid: {bool(project.audit and project.audit.valid)}")
    if project.audit:
        for issue in project.audit.issues:
            print(f"{issue.severity.value.upper()} {issue.code}: {issue.message}")


def run_export(project_id: str, output: Path | None) -> None:
    destination = PosterStudio().export(project_id, output)
    print(f"Export: {destination}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate cricket academy social posts.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    serve = subparsers.add_parser("serve", help="Run the local poster studio web app.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")

    generate = subparsers.add_parser(
        "generate",
        help="Generate one poster from a structured JSON file.",
    )
    generate.add_argument("--input", required=True, type=Path)
    generate.add_argument(
        "--offline",
        action="store_true",
        help="Use deterministic planning and local artwork without API calls.",
    )
    generate.add_argument(
        "--critic",
        action="store_true",
        help="Run up to two GPT-5.4 screenshot-critic passes.",
    )
    generate.add_argument(
        "--theme",
        choices=[mode.value for mode in ColorMode],
        default=ColorMode.DARK.value,
        help="Choose the hybrid poster color mode.",
    )
    generate.add_argument(
        "--font",
        choices=[preset.value for preset in FontPreset],
        help="Override the automatically selected registered font preset.",
    )
    generate.add_argument(
        "--intent",
        choices=[intent.value for intent in StyleIntent],
        help="Visual intent driving colour deployment, type and shape.",
    )

    score = subparsers.add_parser(
        "score",
        help="Render every fixture offline and report deterministic layout scores.",
    )
    score.add_argument(
        "--all-fixtures",
        action="store_true",
        help="Score every JSON fixture (default behaviour).",
    )
    score.add_argument(
        "--fixtures",
        type=Path,
        help="Directory of fixture JSON files. Defaults to ./fixtures.",
    )
    score.add_argument(
        "--output",
        type=Path,
        help="Calibration output directory. Defaults to ./output/calibration.",
    )
    score.add_argument(
        "--theme",
        choices=[mode.value for mode in ColorMode],
        default=ColorMode.DARK.value,
        help="Colour mode to sweep.",
    )
    score.add_argument(
        "--intents",
        help=(
            "Comma-separated visual intents to sweep, or 'all'. Renders every "
            "fixture once per intent."
        ),
    )

    compose = subparsers.add_parser(
        "compose",
        help="Compose a poster from the plate bank, subjects and exact copy.",
    )
    compose.add_argument("--input", required=True, type=Path)
    compose.add_argument(
        "--intent",
        choices=[intent.value for intent in StyleIntent],
        default=StyleIntent.BOLD_ATTENTION.value,
    )
    compose.add_argument(
        "--theme", choices=[mode.value for mode in ColorMode], default=ColorMode.DARK.value
    )
    compose.add_argument(
        "--archetype",
        choices=[archetype.value for archetype in ArchetypeId],
        help="Force a layout archetype instead of matching one to the plate.",
    )
    compose.add_argument("--logo", type=Path)
    compose.add_argument("--plate", help="Use a specific plate file from the bank.")
    compose.add_argument(
        "--subject",
        help=(
            "Comma-separated subject cut-outs from the bank. The first is the "
            "hero; later figures step down in height on the same floor line."
        ),
    )
    compose.add_argument(
        "--bullets",
        choices=["auto", "dots", "feature", "rules"],
        default="auto",
        help="How selling points are set. 'auto' tiles three or more, lists fewer.",
    )
    compose.add_argument("--output", type=Path)

    bank = subparsers.add_parser("bank", help="Rebuild an asset manifest.")
    bank.add_argument("kind", choices=["plates", "subjects"])

    variants = subparsers.add_parser(
        "variants",
        help="Render several meaningfully different posters from one content file.",
    )
    variants.add_argument("--input", required=True, type=Path)
    variants.add_argument("--count", type=int, default=6)
    variants.add_argument("--logo", type=Path)
    variants.add_argument("--output", type=Path, help="Directory for the set.")

    harvest = subparsers.add_parser(
        "harvest",
        help="Lift a reusable layout template off a generated poster.",
    )
    harvest.add_argument("--input", required=True, type=Path, help="Source poster image.")
    harvest.add_argument("--name", help="Template name (defaults to the file stem).")
    harvest.add_argument(
        "--max-passes",
        type=int,
        default=4,
        help="Erase passes allowed before the harvest is rejected.",
    )
    harvest.add_argument(
        "--force",
        action="store_true",
        help="Bank even when text remains on the plate. Rarely what you want.",
    )

    cutout = subparsers.add_parser(
        "cutout",
        help="Cut subjects out of photographs into the subject bank.",
    )
    cutout.add_argument("--input", required=True, type=Path, help="Photo file or directory.")
    cutout.add_argument("--tags", default="", help="Comma-separated tags for selection.")
    cutout.add_argument("--limit", type=int, help="Process only the first N photos.")

    validate = subparsers.add_parser(
        "validate",
        help="Rerun the deterministic audit for a project.",
    )
    validate.add_argument("--project", required=True)

    export = subparsers.add_parser(
        "export",
        help="Export a project ZIP.",
    )
    export.add_argument("--project", required=True)
    export.add_argument("--output", type=Path)
    return parser


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    args = build_parser().parse_args()
    if args.command == "serve":
        run_serve(args.host, args.port, args.reload)
    elif args.command == "generate":
        run_generate(
            args.input,
            offline=args.offline,
            critic=args.critic,
            color_mode=ColorMode(args.theme),
            font_preset=FontPreset(args.font) if args.font else None,
            style_intent=StyleIntent(args.intent) if args.intent else None,
        )
    elif args.command == "score":
        if not args.intents:
            selected = None
        elif args.intents.strip().lower() == "all":
            selected = list(StyleIntent)
        else:
            selected = [
                StyleIntent(value.strip())
                for value in args.intents.split(",")
                if value.strip()
            ]
        run_score(args.fixtures, args.output, selected, ColorMode(args.theme))
    elif args.command == "compose":
        run_compose(
            args.input,
            intent=StyleIntent(args.intent),
            color_mode=ColorMode(args.theme),
            archetype=args.archetype,
            logo=args.logo,
            output=args.output,
            plate=args.plate,
            subject=args.subject,
            bullets=args.bullets,
        )
    elif args.command == "bank":
        run_bank_index(args.kind)
    elif args.command == "cutout":
        run_cutout(args.input, args.tags, args.limit)
    elif args.command == "harvest":
        run_harvest(args.input, args.name, args.max_passes, args.force)
    elif args.command == "variants":
        run_variants(args.input, args.count, args.logo, args.output)
    elif args.command == "validate":
        run_validate(args.project)
    elif args.command == "export":
        run_export(args.project, args.output)


if __name__ == "__main__":
    main()

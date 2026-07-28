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
) -> None:
    from .archetypes import ArchetypeId
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


def run_bank_index(kind: str) -> None:
    if kind == "plates":
        from .plates import index_plates

        bank = index_plates()
        print(f"Indexed {len(bank.entries)} plate(s)")
    else:
        from .subjects import index_subjects

        bank = index_subjects()
        print(f"Indexed {len(bank.entries)} subject(s)")


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
    compose.add_argument("--archetype", choices=["left_column", "bottom_third"])
    compose.add_argument("--logo", type=Path)
    compose.add_argument("--plate", help="Use a specific plate file from the bank.")
    compose.add_argument("--output", type=Path)

    bank = subparsers.add_parser("bank", help="Rebuild an asset manifest.")
    bank.add_argument("kind", choices=["plates", "subjects"])

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
        )
    elif args.command == "bank":
        run_bank_index(args.kind)
    elif args.command == "validate":
        run_validate(args.project)
    elif args.command == "export":
        run_export(args.project, args.output)


if __name__ == "__main__":
    main()

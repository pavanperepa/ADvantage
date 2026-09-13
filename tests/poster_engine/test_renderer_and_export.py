from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from cricket_posts.models import (
    AuditSeverity,
    ColorMode,
    ContentSection,
    FontPreset,
    GenerationMode,
    InformationContent,
    ProjectStatus,
    parse_poster_content,
)
from cricket_posts.studio import PosterStudio
from cricket_posts.studio_renderer import RenderJob


FIXTURES = [
    "information.json",
    "tournament-registration.json",
    "coaching-services.json",
    "lane-rental.json",
    "summer-camp.json",
    "svats-cup.json",
]


@pytest.mark.parametrize("filename", FIXTURES)
def test_all_layout_families_render_one_valid_1080x1350_poster(
    tmp_path,
    filename,
    load_content,
):
    studio = PosterStudio(
        database_path=tmp_path / filename / "studio.db",
        output_root=tmp_path / filename / "projects",
    )
    brand = studio.ensure_default_brand()
    project = studio.create_from_content(
        load_content(filename),
        brand.id,
        use_ai_planner=False,
    )
    rendered = studio.generate(project.id, use_ideogram=False)

    assert rendered.status == ProjectStatus.COMPLETE
    assert rendered.audit is not None
    assert rendered.audit.valid
    assert rendered.audit.checks["protected_copy"]
    assert rendered.audit.checks["safe_margins_and_overflow"]
    assert rendered.audit.checks["minimum_body_size"]
    assert rendered.audit.checks["contrast"]
    assert rendered.audit.measured["png_dimensions"] == [1080, 1350]
    assert rendered.audit.measured["minimum_body_px"] >= 24

    # Measurement foundation: geometry and score ride along with every audit.
    geometry = rendered.audit.geometry
    assert geometry is not None
    assert geometry.regions and geometry.ink_rects and geometry.text_backdrops
    region_ids = {region.region_id for region in geometry.regions}
    assert {"header", "hero", "body", "footer"} <= region_ids
    assert any(region_id.startswith("body.card.") for region_id in region_ids)
    assert all(backdrop.sample_count > 0 for backdrop in geometry.text_backdrops)

    score = rendered.audit.score
    assert score is not None
    assert 0.0 <= score.total <= 1.0
    assert {metric.name for metric in score.metrics} >= {
        "whitespace",
        "balance",
        "alignment",
        "spacing_consistency",
        "crowding",
        "hierarchy",
        "text_backdrop_contrast",
        "backdrop_busyness",
    }
    # Pixel-measured contrast is recorded but not yet a gate, so the key must be
    # present while its value stays free to be either.
    assert "contrast_measured" in rendered.audit.checks
    assert rendered.audit.measured["minimum_contrast_measured"] is not None


def test_unreadable_density_stops_with_field_level_revision_report(tmp_path):
    studio = PosterStudio(
        database_path=tmp_path / "studio.db",
        output_root=tmp_path / "projects",
    )
    brand = studio.ensure_default_brand()
    content = InformationContent(
        title="Everything About Our Academy",
        subtitle="All program information must remain on one poster.",
        sections=[
            ContentSection(
                heading=f"PROGRAM SECTION {index}",
                text=" ".join(["Detailed training information"] * 18),
                items=[f"Required item {index}-{item} with more detail" for item in range(12)],
            )
            for index in range(8)
        ],
    )
    project = studio.create_from_content(content, brand.id, use_ai_planner=False)
    rendered = studio.generate(project.id, use_ideogram=False)

    assert rendered.status == ProjectStatus.NEEDS_REVISION
    assert rendered.audit is not None
    assert not rendered.audit.valid
    assert any(issue.code == "content_overflow" for issue in rendered.audit.issues)
    assert rendered.error is not None
    assert "one page" in rendered.error


def test_warnings_are_reported_without_failing_the_audit(tmp_path, load_content):
    studio = PosterStudio(
        database_path=tmp_path / "studio.db",
        output_root=tmp_path / "projects",
    )
    brand = studio.ensure_default_brand()
    project = studio.create_from_content(
        load_content("summer-camp.json"),
        brand.id,
        use_ai_planner=False,
    )
    rendered = studio.generate(project.id, use_ideogram=False)

    assert rendered.audit is not None
    assert rendered.audit.valid
    assert all(
        issue.severity == AuditSeverity.WARNING
        for issue in rendered.audit.issues
    )
    # The aesthetic score never contributes to validity.
    assert rendered.audit.score is not None


def test_render_batch_reuses_one_browser_for_many_posters(tmp_path, load_content):
    studio = PosterStudio(
        database_path=tmp_path / "studio.db",
        output_root=tmp_path / "projects",
    )
    brand = studio.ensure_default_brand()
    jobs = []
    for filename in ("information.json", "lane-rental.json"):
        project = studio.create_from_content(
            load_content(filename),
            brand.id,
            use_ai_planner=False,
        )
        rendered = studio.generate(project.id, use_ideogram=False)
        assert rendered.html_path and rendered.poster_path
        jobs.append(
            RenderJob(
                html_path=Path(rendered.html_path),
                png_path=Path(rendered.poster_path),
                project=rendered,
                brand=brand,
            )
        )

    reports = studio.renderer.render_batch(jobs)

    assert len(reports) == len(jobs)
    assert all(report.valid for report in reports)
    assert all(report.score is not None for report in reports)
    assert all(report.geometry is not None for report in reports)


def test_export_zip_contains_editable_source_art_and_audit(tmp_path, load_content):
    studio = PosterStudio(
        database_path=tmp_path / "studio.db",
        output_root=tmp_path / "projects",
    )
    brand = studio.ensure_default_brand()
    project = studio.create_from_content(
        load_content("information.json"),
        brand.id,
        use_ai_planner=False,
    )
    rendered = studio.generate(project.id, use_ideogram=False)
    destination = studio.export(rendered.id, tmp_path / "poster-project.zip")

    with zipfile.ZipFile(destination) as archive:
        names = set(archive.namelist())
        assert {
            "project.json",
            "design-spec.json",
            "validation-report.json",
            "generation-metadata.json",
            "poster.png",
            "poster.html",
            "artwork.svg",
        }.issubset(names)
        project_payload = json.loads(archive.read("project.json"))
        assert project_payload["id"] == rendered.id
        assert project_payload["audit"]["valid"] is True


def test_light_vignette_render_creates_intent_pngs(tmp_path):
    payload = json.loads(
        (
            Path(__file__).parents[2]
            / "fixtures"
            / "foundation-program-houston.json"
        ).read_text(encoding="utf-8")
    )
    studio = PosterStudio(
        database_path=tmp_path / "studio.db",
        output_root=tmp_path / "projects",
    )
    brand = studio.save_brand(
        studio.ensure_default_brand().model_copy(
            update={
                "name": payload["brand"]["name"],
                "contact_lines": [],
                "logo_path": None,
            }
        )
    )
    project = studio.create_from_content(
        parse_poster_content(payload["content"]),
        brand.id,
        use_ai_planner=False,
    )
    rendered = studio.generate(
        project.id,
        use_ideogram=False,
        color_mode=ColorMode.LIGHT,
        font_preset=FontPreset.MODERN,
    )

    assert rendered.status == ProjectStatus.COMPLETE
    assert rendered.audit is not None and rendered.audit.valid
    assert rendered.design is not None
    assert rendered.design.color_mode == ColorMode.LIGHT
    assert rendered.design.font_preset == FontPreset.MODERN
    icon_paths = list(
        (tmp_path / "projects" / project.id / "intent-icons").glob("*.png")
    )
    assert len(icon_paths) >= 4
    assert all(path.stat().st_size > 0 for path in icon_paths)

from __future__ import annotations

import json
import shutil
import threading
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image

from .ideogram import generate_studio_art
from .layout import layout_summary, plan_design
from .models import (
    AuditIssue,
    AuditSeverity,
    BrandProfile,
    ColorMode,
    FontPreset,
    GenerationMode,
    PosterContent,
    PosterProject,
    ProjectStatus,
    StyleIntent,
    ValidationReport,
    protect_all_copy,
)
from .openai_studio import OpenAIStudioProvider, apply_critic_patch, critic_issues
from .theme import build_theme
from .renderer import ASSET_DIR, PROJECT_ROOT
from .storage import StudioDatabase
from .studio_renderer import PlaywrightRenderer


class PosterStudio:
    def __init__(
        self,
        *,
        database_path: Path | None = None,
        output_root: Path | None = None,
        openai_provider: OpenAIStudioProvider | None = None,
        renderer: PlaywrightRenderer | None = None,
    ) -> None:
        self.output_root = output_root or PROJECT_ROOT / "output" / "projects"
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.database = StudioDatabase(database_path or PROJECT_ROOT / "studio.db")
        self.database.recover_interrupted()
        self._openai_provider = openai_provider
        self.renderer = renderer or PlaywrightRenderer()
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self.ensure_default_brand()

    @property
    def openai_provider(self) -> OpenAIStudioProvider:
        if self._openai_provider is None:
            self._openai_provider = OpenAIStudioProvider()
        return self._openai_provider

    def ensure_default_brand(self) -> BrandProfile:
        brands = self.database.list_brands()
        if brands:
            return brands[0]
        return self.database.save_brand(
            BrandProfile(
                name="ADvantage",
                logo_path=str(ASSET_DIR / "mark.svg"),
            )
        )

    def save_brand(self, brand: BrandProfile) -> BrandProfile:
        return self.database.save_brand(brand)

    def create_from_source(self, source_text: str, brand_id: str) -> PosterProject:
        content = self.openai_provider.extract(source_text)
        brand = self.database.get_brand(brand_id)
        suggestion = self.openai_provider.plan(content)
        design = plan_design(content, brand, suggestion)
        project = PosterProject(
            brand_id=brand_id,
            source_text=source_text,
            content=content,
            design=design,
            status=ProjectStatus.READY,
        )
        return self.database.save_project(project)

    def create_from_content(
        self,
        content: PosterContent,
        brand_id: str,
        *,
        source_text: str = "",
        use_ai_planner: bool = True,
    ) -> PosterProject:
        brand = self.database.get_brand(brand_id)
        protected = protect_all_copy(content)
        suggestion = self.openai_provider.plan(protected) if use_ai_planner else None
        project = PosterProject(
            brand_id=brand_id,
            source_text=source_text,
            content=protected,
            design=plan_design(protected, brand, suggestion),
            status=ProjectStatus.READY,
        )
        return self.database.save_project(project)

    def update_content(
        self,
        project_id: str,
        content: PosterContent,
    ) -> PosterProject:
        project = self.database.get_project(project_id)
        brand = self.database.get_brand(project.brand_id)
        protected = protect_all_copy(content)
        previous = project.design
        project.content = protected
        # Editing copy must not silently discard the chosen look.
        project.design = plan_design(
            protected,
            brand,
            style_intent=previous.style_intent if previous else None,
            color_mode=previous.color_mode if previous else ColorMode.DARK,
            font_preset=previous.font_preset if previous else None,
        )
        project.status = ProjectStatus.READY
        project.html_path = None
        project.poster_path = None
        project.audit = None
        project.error = None
        return self.database.save_project(project)

    def _project_lock(self, project_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(project_id, threading.Lock())

    def _project_dir(self, project_id: str) -> Path:
        return self.output_root / project_id

    def _fallback_art(self, project: PosterProject, destination: Path) -> Path:
        if project.design is None:
            raise ValueError("Project has no DesignSpec.")
        mapping = {
            "announcement_hero": ASSET_DIR / "information-background.svg",
            "tournament_registration": ASSET_DIR / "tournament-background.svg",
            "tournament_category_grid": ASSET_DIR / "tournament-background.svg",
            "summer_camp": ASSET_DIR / "services-background.svg",
            "coaching_services": ASSET_DIR / "services-background.svg",
            "lane_rental": ASSET_DIR / "information-background.svg",
        }
        source = mapping[project.design.family.value]
        fallback_destination = destination.with_suffix(".svg")
        fallback_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, fallback_destination)
        return fallback_destination

    def generate(
        self,
        project_id: str,
        *,
        use_ideogram: bool = True,
        use_critic: bool = False,
        regenerate_art: bool = False,
        render_mode: GenerationMode | str | None = None,
        color_mode: ColorMode | str | None = None,
        font_preset: FontPreset | str | None = None,
        style_intent: StyleIntent | str | None = None,
    ) -> PosterProject:
        lock = self._project_lock(project_id)
        if not lock.acquire(blocking=False):
            raise RuntimeError("This project is already generating.")
        try:
            project = self.database.get_project(project_id)
            brand = self.database.get_brand(project.brand_id)
            if project.design is None:
                project.design = plan_design(project.content, brand)
            if (
                style_intent is not None
                or color_mode is not None
                or font_preset is not None
            ):
                current = project.design
                resolved_intent = (
                    StyleIntent(style_intent)
                    if style_intent is not None
                    else current.style_intent
                )
                resolved_mode = (
                    ColorMode(color_mode)
                    if color_mode is not None
                    else current.color_mode
                )
                # An explicit font wins. Otherwise switching intent re-picks the
                # typeface from the new recipe, while a pure colour change keeps
                # whatever typeface the poster already had.
                if font_preset is not None:
                    font_override = FontPreset(font_preset)
                elif resolved_intent != current.style_intent:
                    font_override = None
                else:
                    font_override = current.font_preset
                theme = build_theme(
                    resolved_intent,
                    brand.palette,
                    resolved_mode,
                    font_override,
                )
                project.design = current.model_copy(
                    update={
                        "style_intent": resolved_intent,
                        "color_mode": resolved_mode,
                        "font_preset": theme.font_preset,
                        "theme": theme,
                        "tokens": current.tokens.model_copy(
                            update={"panel_opacity": theme.panel_opacity}
                        ),
                    }
                )
                project.html_path = None
                project.poster_path = None
            requested_mode = (
                GenerationMode(render_mode) if render_mode is not None else project.render_mode
            )
            if requested_mode != project.render_mode:
                project.artwork_path = None
                project.html_path = None
                project.poster_path = None
                project.audit = None
            project.render_mode = requested_mode
            project.generation_metadata["classification"] = layout_summary(project.content)
            project_dir = self._project_dir(project.id)
            project_dir.mkdir(parents=True, exist_ok=True)
            project.error = None

            artwork_path = Path(project.artwork_path) if project.artwork_path else None
            if regenerate_art or artwork_path is None or not artwork_path.exists():
                project.status = ProjectStatus.GENERATING_ART
                self.database.save_project(project)
                if use_ideogram:
                    result = generate_studio_art(
                        project.design,
                        project_dir / "artwork.png",
                    )
                    artwork_path = Path(result.path)
                    project.generation_metadata["ideogram"] = result.model_dump(mode="json")
                else:
                    artwork_path = self._fallback_art(
                        project,
                        project_dir / "artwork.png",
                    )
                    project.generation_metadata["ideogram"] = {
                        "mode": "offline_fallback",
                    }
                project.artwork_path = str(artwork_path)
                self.database.save_project(project)

            project.status = ProjectStatus.RENDERING
            self.database.save_project(project)
            html_path = self.renderer.write_html(
                project,
                brand,
                artwork_path,
                project_dir / "poster.html",
            )
            poster_path = project_dir / "poster.png"
            project.html_path = str(html_path)
            project.poster_path = str(poster_path)

            project.status = ProjectStatus.VALIDATING
            self.database.save_project(project)
            report = self.renderer.render_and_measure(
                html_path,
                poster_path,
                project,
                brand,
            )
            project.audit = report
            if not report.valid:
                project.status = ProjectStatus.NEEDS_REVISION
                project.error = (
                    "The poster could not fit all supplied copy legibly on one page. "
                    "Review the validation issues, shorten or omit the flagged fields, "
                    "then rerender."
                )
                return self.database.save_project(project)

            critic_history: list[dict[str, Any]] = []
            if use_critic:
                for _ in range(2):
                    critic_result = self.openai_provider.critique(poster_path, project.design)
                    critic_history.append(critic_result.model_dump(mode="json"))
                    updated_design = apply_critic_patch(project.design, critic_result)
                    if updated_design == project.design:
                        break
                    project.design = updated_design
                    html_path = self.renderer.write_html(
                        project,
                        brand,
                        artwork_path,
                        html_path,
                    )
                    report = self.renderer.render_and_measure(
                        html_path,
                        poster_path,
                        project,
                        brand,
                    )
                    report.issues.extend(critic_issues(critic_result))
                    project.audit = report
                    if not report.valid:
                        project.status = ProjectStatus.NEEDS_REVISION
                        project.error = "A visual refinement caused a validation failure."
                        break
                project.generation_metadata["critic_passes"] = critic_history

            if project.audit and project.audit.valid:
                project.status = ProjectStatus.COMPLETE
                project.error = None
            return self.database.save_project(project)
        except Exception as exc:
            project = self.database.get_project(project_id)
            project.status = ProjectStatus.FAILED
            project.error = str(exc)
            self.database.save_project(project)
            raise
        finally:
            lock.release()

    def validate(self, project_id: str) -> PosterProject:
        project = self.database.get_project(project_id)
        if not project.html_path or not project.poster_path or not project.artwork_path:
            raise RuntimeError("Project has not been rendered yet.")
        brand = self.database.get_brand(project.brand_id)
        project.status = ProjectStatus.VALIDATING
        self.database.save_project(project)
        project.audit = self.renderer.render_and_measure(
            Path(project.html_path),
            Path(project.poster_path),
            project,
            brand,
        )
        project.status = (
            ProjectStatus.COMPLETE
            if project.audit.valid
            else ProjectStatus.NEEDS_REVISION
        )
        return self.database.save_project(project)

    def export(self, project_id: str, destination: Path | None = None) -> Path:
        project = self.database.get_project(project_id)
        if not project.poster_path or not Path(project.poster_path).exists():
            raise RuntimeError("Project has no rendered poster to export.")
        export_dir = PROJECT_ROOT / "output" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        destination = destination or export_dir / f"{project.id}.zip"
        destination.parent.mkdir(parents=True, exist_ok=True)

        project_dir = self._project_dir(project.id)
        manifest_path = project_dir / "project.json"
        manifest_path.write_text(
            json.dumps(project.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        design_path = project_dir / "design-spec.json"
        design_path.write_text(
            json.dumps(
                project.design.model_dump(mode="json") if project.design else {},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        audit_path = project_dir / "validation-report.json"
        audit_path.write_text(
            json.dumps(
                project.audit.model_dump(mode="json") if project.audit else {},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        metadata_path = project_dir / "generation-metadata.json"
        metadata_path.write_text(
            json.dumps(project.generation_metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        files = [
            manifest_path,
            design_path,
            audit_path,
            metadata_path,
            Path(project.poster_path),
        ]
        if project.html_path:
            files.append(Path(project.html_path))
        if project.artwork_path:
            files.append(Path(project.artwork_path))
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                if path.exists():
                    archive.write(path, path.name)
        return destination

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict

from .campaign_api import router as campaign_router
from .layout import layout_summary
from .models import (
    BrandProfile,
    ColorMode,
    FontPreset,
    GenerationMode,
    Palette,
    StyleIntent,
    parse_editable_content,
)
from .renderer import ASSET_DIR, PROJECT_ROOT, TEMPLATE_DIR
from .studio import PosterStudio


WEB_TEMPLATE_DIR = TEMPLATE_DIR / "web"
BRAND_ASSET_DIR = PROJECT_ROOT / "output" / "brand-assets"

STYLE_INTENT_CHOICES: tuple[tuple[str, str], ...] = (
    (StyleIntent.BOLD_ATTENTION.value, "Bold and attention-grabbing"),
    (StyleIntent.BRIGHT_VIBRANT.value, "Bright and colourful"),
    (StyleIntent.MINIMAL_CLEAN.value, "Minimal and neutral"),
    (StyleIntent.PREMIUM_ELEGANT.value, "Premium and elegant"),
    (StyleIntent.PROFESSIONAL_CLEAN.value, "Professional and clean"),
    (StyleIntent.YOUTHFUL_ENERGETIC.value, "Youthful and energetic"),
    (StyleIntent.PLAYFUL_FUN.value, "Playful and fun"),
    (StyleIntent.MODERN_SLEEK.value, "Modern and sleek"),
)

FONT_PRESET_CHOICES: tuple[tuple[str, str], ...] = (
    (FontPreset.ATHLETIC.value, "Athletic — Anton"),
    (FontPreset.CONDENSED.value, "Condensed — Bebas Neue"),
    (FontPreset.IMPACT.value, "Impact — Archivo Black"),
    (FontPreset.MODERN.value, "Modern — Space Grotesk"),
    (FontPreset.GEOMETRIC.value, "Geometric — Outfit"),
    (FontPreset.ROUNDED.value, "Rounded — Poppins"),
    (FontPreset.EDITORIAL.value, "Editorial — Playfair Display"),
    (FontPreset.FRIENDLY.value, "Friendly — Fraunces"),
)


class ExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand_id: str
    source_text: str


class StructuredProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand_id: str
    content: dict[str, Any]
    source_text: str = ""
    use_ai_planner: bool = True


class ContentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: dict[str, Any]


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    use_ideogram: bool = True
    use_critic: bool = False
    render_mode: GenerationMode = GenerationMode.HYBRID
    color_mode: ColorMode | None = None
    font_preset: FontPreset | None = None
    style_intent: StyleIntent | None = None


def _get_project(studio: PosterStudio, project_id: str):
    try:
        return studio.database.get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _generate_background(
    studio: PosterStudio,
    project_id: str,
    use_ideogram: bool,
    use_critic: bool,
    regenerate_art: bool,
    render_mode: GenerationMode | str | None,
    color_mode: ColorMode | str | None = None,
    font_preset: FontPreset | str | None = None,
    style_intent: StyleIntent | str | None = None,
) -> None:
    try:
        studio.generate(
            project_id,
            use_ideogram=use_ideogram,
            use_critic=use_critic,
            regenerate_art=regenerate_art,
            render_mode=render_mode,
            color_mode=color_mode,
            font_preset=font_preset,
            style_intent=style_intent,
        )
    except Exception:
        # PosterStudio records a safe error and failed status. BackgroundTasks
        # has no caller to receive an exception, so do not re-raise it here.
        return


def create_app(studio: PosterStudio | None = None) -> FastAPI:
    studio = studio or PosterStudio()
    app = FastAPI(
        title="ADvantage Creative Studio",
        version="1.0.0",
        description="Verified static-ad production with exact deterministic copy.",
    )
    app.state.studio = studio
    templates = Jinja2Templates(directory=WEB_TEMPLATE_DIR)
    app.mount("/assets", StaticFiles(directory=ASSET_DIR), name="assets")

    # The Next.js frontend (P1-06 UI work) runs on its own dev server and
    # calls this JSON API directly rather than through a proxy/rewrite.
    app.add_middleware(
        CORSMiddleware,
        # Both spellings of the dev origin: a browser treats localhost and
        # 127.0.0.1 as different origins, and which one appears depends on how
        # the developer opened the page.
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(campaign_router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "brands": studio.database.list_brands(),
                "projects": studio.database.list_projects(),
            },
        )

    @app.post("/brands")
    def create_brand_form(
        name: str = Form(...),
        tagline: str = Form(""),
        location: str = Form(""),
        contact_lines: str = Form(""),
        ink: str = Form("#071426"),
        surface: str = Form("#F6F1E6"),
        accent: str = Form("#FFD23F"),
        highlight: str = Form("#21C7FF"),
        logo: UploadFile | None = File(None),
    ) -> RedirectResponse:
        brand = BrandProfile(
            name=name,
            tagline=tagline,
            location=location,
            contact_lines=[
                line.strip() for line in contact_lines.splitlines() if line.strip()
            ],
            logo_path=str(ASSET_DIR / "mark.svg"),
            palette=Palette(
                ink=ink,
                surface=surface,
                accent=accent,
                highlight=highlight,
            ),
        )
        if logo and logo.filename:
            suffix = Path(logo.filename).suffix.lower()
            if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
                raise HTTPException(
                    status_code=422,
                    detail="Logo must be PNG, JPEG, WebP, or SVG.",
                )
            data = logo.file.read(5_000_001)
            if len(data) > 5_000_000:
                raise HTTPException(status_code=422, detail="Logo must be 5 MB or smaller.")
            destination = BRAND_ASSET_DIR / brand.id / f"logo{suffix}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            brand.logo_path = str(destination)
        studio.save_brand(brand)
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    @app.post("/projects/extract")
    def extract_form(
        brand_id: str = Form(...),
        source_text: str = Form(...),
    ) -> RedirectResponse:
        try:
            project = studio.create_from_source(source_text, brand_id)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return RedirectResponse(
            f"/projects/{project.id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    def project_page(request: Request, project_id: str) -> HTMLResponse:
        project = _get_project(studio, project_id)
        brand = studio.database.get_brand(project.brand_id)
        return templates.TemplateResponse(
            request=request,
            name="project.html",
            context={
                "project": project,
                "brand": brand,
                "classification": layout_summary(project.content),
                "style_intents": STYLE_INTENT_CHOICES,
                "font_presets": FONT_PRESET_CHOICES,
                "content_json": json.dumps(
                    project.content.model_dump(mode="json"),
                    indent=2,
                    ensure_ascii=False,
                ),
            },
        )

    @app.post("/projects/{project_id}/content")
    def update_content_form(
        project_id: str,
        content_json: str = Form(...),
    ) -> RedirectResponse:
        try:
            content = parse_editable_content(json.loads(content_json))
            studio.update_content(project_id, content)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return RedirectResponse(
            f"/projects/{project_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.post("/projects/{project_id}/generate")
    def generate_form(
        project_id: str,
        background_tasks: BackgroundTasks,
        use_ideogram: bool = Form(False),
        use_critic: bool = Form(False),
        render_mode: str = Form(GenerationMode.HYBRID.value),
        color_mode: str = Form(ColorMode.DARK.value),
        font_preset: str = Form(FontPreset.ATHLETIC.value),
        style_intent: str = Form(""),
    ) -> RedirectResponse:
        _get_project(studio, project_id)
        background_tasks.add_task(
            _generate_background,
            studio,
            project_id,
            use_ideogram,
            use_critic,
            False,
            render_mode,
            color_mode,
            font_preset,
            style_intent or None,
        )
        return RedirectResponse(
            f"/projects/{project_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.post("/projects/{project_id}/rerender")
    def rerender_form(
        project_id: str,
        background_tasks: BackgroundTasks,
    ) -> RedirectResponse:
        _get_project(studio, project_id)
        background_tasks.add_task(
            _generate_background,
            studio,
            project_id,
            False,
            False,
            False,
            None,
        )
        return RedirectResponse(
            f"/projects/{project_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.post("/projects/{project_id}/regenerate-art")
    def regenerate_art_form(
        project_id: str,
        background_tasks: BackgroundTasks,
    ) -> RedirectResponse:
        _get_project(studio, project_id)
        background_tasks.add_task(
            _generate_background,
            studio,
            project_id,
            True,
            False,
            True,
            None,
        )
        return RedirectResponse(
            f"/projects/{project_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    @app.get("/projects/{project_id}/poster.png")
    def project_poster(project_id: str) -> FileResponse:
        project = _get_project(studio, project_id)
        if not project.poster_path or not Path(project.poster_path).exists():
            raise HTTPException(status_code=404, detail="Poster has not been rendered.")
        return FileResponse(project.poster_path, media_type="image/png")

    @app.get("/projects/{project_id}/artwork")
    def project_artwork(project_id: str) -> FileResponse:
        project = _get_project(studio, project_id)
        if not project.artwork_path or not Path(project.artwork_path).exists():
            raise HTTPException(status_code=404, detail="Artwork has not been generated.")
        return FileResponse(project.artwork_path)

    @app.get("/projects/{project_id}/export")
    def export_form(project_id: str) -> FileResponse:
        try:
            export_path = studio.export(project_id)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return FileResponse(
            export_path,
            media_type="application/zip",
            filename=export_path.name,
        )

    @app.get("/api/brands")
    def list_brands_api() -> list[BrandProfile]:
        return studio.database.list_brands()

    @app.post("/api/brands", status_code=status.HTTP_201_CREATED)
    def create_brand_api(brand: BrandProfile) -> BrandProfile:
        return studio.save_brand(brand)

    @app.get("/api/projects")
    def list_projects_api():
        return studio.database.list_projects()

    @app.get("/api/projects/{project_id}")
    def get_project_api(project_id: str):
        return _get_project(studio, project_id)

    @app.post("/api/extract", status_code=status.HTTP_201_CREATED)
    def extract_api(payload: ExtractionRequest):
        try:
            return studio.create_from_source(payload.source_text, payload.brand_id)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/projects", status_code=status.HTTP_201_CREATED)
    def create_project_api(payload: StructuredProjectRequest):
        try:
            return studio.create_from_content(
                parse_editable_content(payload.content),
                payload.brand_id,
                source_text=payload.source_text,
                use_ai_planner=payload.use_ai_planner,
            )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.put("/api/projects/{project_id}/content")
    def update_content_api(project_id: str, payload: ContentUpdateRequest):
        try:
            return studio.update_content(
                project_id,
                parse_editable_content(payload.content),
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post(
        "/api/projects/{project_id}/generate",
        status_code=status.HTTP_202_ACCEPTED,
    )
    def generate_api(
        project_id: str,
        payload: GenerationRequest,
        background_tasks: BackgroundTasks,
    ) -> dict[str, str]:
        _get_project(studio, project_id)
        background_tasks.add_task(
            _generate_background,
            studio,
            project_id,
            payload.use_ideogram,
            payload.use_critic,
            False,
            payload.render_mode,
            payload.color_mode,
            payload.font_preset,
            payload.style_intent,
        )
        return {"project_id": project_id, "status": "accepted"}

    @app.post(
        "/api/projects/{project_id}/rerender",
        status_code=status.HTTP_202_ACCEPTED,
    )
    def rerender_api(
        project_id: str,
        background_tasks: BackgroundTasks,
    ) -> dict[str, str]:
        _get_project(studio, project_id)
        background_tasks.add_task(
            _generate_background,
            studio,
            project_id,
            False,
            False,
            False,
            None,
        )
        return {"project_id": project_id, "status": "accepted"}

    @app.post(
        "/api/projects/{project_id}/regenerate-art",
        status_code=status.HTTP_202_ACCEPTED,
    )
    def regenerate_art_api(
        project_id: str,
        background_tasks: BackgroundTasks,
    ) -> dict[str, str]:
        _get_project(studio, project_id)
        background_tasks.add_task(
            _generate_background,
            studio,
            project_id,
            True,
            False,
            True,
            None,
        )
        return {"project_id": project_id, "status": "accepted"}

    @app.post("/api/projects/{project_id}/validate")
    def validate_api(project_id: str):
        try:
            return studio.validate(project_id)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/projects/{project_id}/export")
    def export_api(project_id: str) -> FileResponse:
        return export_form(project_id)

    return app


app = create_app()

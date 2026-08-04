from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, TypeAlias
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


class Palette(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ink: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    surface: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    accent: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    highlight: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class ContentType(str, Enum):
    INFORMATION = "information"
    TOURNAMENT = "tournament"
    CAMP = "camp"
    COACHING = "coaching"
    LANE_RENTAL = "lane_rental"


class LayoutFamily(str, Enum):
    ANNOUNCEMENT_HERO = "announcement_hero"
    TOURNAMENT_REGISTRATION = "tournament_registration"
    TOURNAMENT_CATEGORY_GRID = "tournament_category_grid"
    SUMMER_CAMP = "summer_camp"
    COACHING_SERVICES = "coaching_services"
    LANE_RENTAL = "lane_rental"


class Density(str, Enum):
    SPACIOUS = "spacious"
    COMPACT = "compact"
    DENSE = "dense"


class CompositionMode(str, Enum):
    ART_FORWARD = "art_forward"
    BALANCED = "balanced"
    INFORMATION_DENSE = "information_dense"


class GenerationMode(str, Enum):
    HYBRID = "hybrid"


class ColorMode(str, Enum):
    DARK = "dark"
    LIGHT = "light"


class FontPreset(str, Enum):
    ATHLETIC = "athletic"
    MODERN = "modern"
    GEOMETRIC = "geometric"
    EDITORIAL = "editorial"
    IMPACT = "impact"
    CONDENSED = "condensed"
    FRIENDLY = "friendly"
    ROUNDED = "rounded"


class StyleIntent(str, Enum):
    """How the poster should feel, supplied alongside the copy.

    Two posters carrying identical information should be able to look completely
    different, so visual intent is a first-class input rather than something
    inferred from the content.
    """

    BRIGHT_VIBRANT = "bright_vibrant"
    MINIMAL_CLEAN = "minimal_clean"
    PREMIUM_ELEGANT = "premium_elegant"
    BOLD_ATTENTION = "bold_attention"
    PROFESSIONAL_CLEAN = "professional_clean"
    YOUTHFUL_ENERGETIC = "youthful_energetic"
    PLAYFUL_FUN = "playful_fun"
    MODERN_SLEEK = "modern_sleek"


class Decoration(str, Enum):
    NONE = "none"
    GRADIENT = "gradient"
    SHAPES = "shapes"
    DIAGONAL = "diagonal"
    SPOTLIGHT = "spotlight"


class ThemeColors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bg: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    panel: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    panel_border: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    text: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    text_muted: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    heading: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    accent: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_text: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    highlight: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    highlight_text: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    # Photo-mount colour for the vignette, always opposed to the background so
    # the frame stays visible in both light and dark modes.
    frame: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    #: The surface the body copy was contrast-solved against. Equals `panel`
    #: unless a measured plate zone was supplied.
    backdrop: str = Field(default="#000000", pattern=r"^#[0-9A-Fa-f]{6}$")


class ThemePack(BaseModel):
    """Resolved look for one poster: colours, type treatment and shape.

    Brand hues are never replaced, only redeployed. What changes between intents
    is how dominant the accent is, how the type is set, and how much shape and
    decoration the design carries.
    """

    model_config = ConfigDict(extra="forbid")

    intent: StyleIntent
    font_preset: FontPreset
    colors: ThemeColors
    display_weight: int = Field(default=700, ge=300, le=900)
    # Deliberately no case control. Chrome's innerText reflects text-transform,
    # so restyling copy to uppercase would break the protected-copy audit and,
    # more importantly, silently alter the wording the academy supplied.
    display_tracking: float = Field(default=0.0, ge=-0.06, le=0.12)
    body_weight: int = Field(default=400, ge=300, le=700)
    radius_px: int = Field(default=0, ge=0, le=44)
    border_width_px: int = Field(default=1, ge=0, le=6)
    accent_bar_px: int = Field(default=5, ge=0, le=14)
    panel_opacity: float = Field(default=0.88, ge=0.55, le=1.0)
    shadow_strength: float = Field(default=0.2, ge=0.0, le=0.6)
    spacing_bias: float = Field(default=1.0, ge=0.8, le=1.35)
    decoration: Decoration = Decoration.GRADIENT


class VisualTreatment(str, Enum):
    HERO = "hero"
    VIGNETTE = "vignette"


class IntentKind(str, Enum):
    STRENGTH = "strength"
    COORDINATION = "coordination"
    LEARNING = "learning"
    FUN = "fun"
    BATTING = "batting"
    BOWLING = "bowling"
    FITNESS = "fitness"
    COACHING = "coaching"
    FRIENDSHIP = "friendship"
    CONFIDENCE = "confidence"
    SCHEDULE = "schedule"
    REGISTRATION = "registration"
    TROPHY = "trophy"
    FACILITY = "facility"
    CONTACT = "contact"
    LOCATION = "location"
    GENERIC = "generic"


class VisualIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_text: str = Field(min_length=1, max_length=240)
    kind: IntentKind


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    GENERATING_ART = "generating_art"
    RENDERING = "rendering"
    VALIDATING = "validating"
    COMPLETE = "complete"
    NEEDS_REVISION = "needs_revision"
    FAILED = "failed"


class BrandProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = Field(min_length=1, max_length=80)
    tagline: str = Field(default="", max_length=140)
    location: str = Field(default="", max_length=180)
    contact_lines: list[str] = Field(default_factory=list, max_length=5)
    logo_path: str | None = None
    #: Where a scan should land, in full — including any routing parameters.
    #: Deliberately separate from the link printed on the poster: that one is
    #: short so a person can type it, this one carries everything needed to
    #: attribute a signup to the post that earned it.
    registration_url: str | None = None
    palette: Palette = Field(
        default_factory=lambda: Palette(
            ink="#071426",
            surface="#F6F1E6",
            accent="#FFD23F",
            highlight="#21C7FF",
        )
    )


class Contact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="", max_length=80)
    phone: str = Field(default="", max_length=50)
    email: str = Field(default="", max_length=120)
    role: str = Field(default="", max_length=80)
    display_text: str = Field(default="", max_length=220)

    def display(self) -> str:
        if self.display_text:
            return self.display_text
        identity = " — ".join(part for part in (self.name, self.role) if part)
        connection = " · ".join(part for part in (self.phone, self.email) if part)
        return " — ".join(part for part in (identity, connection) if part)


class Schedule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str = Field(default="", max_length=100)
    days: str = Field(default="", max_length=100)
    time: str = Field(default="", max_length=100)
    display_text: str = Field(default="", max_length=320)

    def display(self) -> str:
        if self.display_text:
            return self.display_text
        return " | ".join(part for part in (self.date, self.days, self.time) if part)


class Prize(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=100)
    value: str = Field(default="", max_length=120)
    display_text: str = Field(default="", max_length=240)

    def display(self) -> str:
        if self.display_text:
            return self.display_text
        return f"{self.label} {self.value}".strip()


class ContentSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = Field(default="", max_length=100)
    text: str = Field(default="", max_length=700)
    items: list[str] = Field(default_factory=list, max_length=12)


class EventCategory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    registration_fee: str = Field(default="", max_length=100)
    contacts: list[Contact] = Field(default_factory=list, max_length=5)
    prizes: list[Prize] = Field(default_factory=list, max_length=10)
    awards_heading: str = Field(default="Individual Awards", max_length=100)
    awards: list[str] = Field(default_factory=list, max_length=15)


class BasePosterContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization: str = Field(default="", max_length=100)
    eyebrow: str = Field(default="", max_length=80)
    title: str = Field(min_length=1, max_length=180)
    subtitle: str = Field(default="", max_length=240)
    tagline: str = Field(default="", max_length=180)
    schedule: Schedule | None = None
    price_line: str = Field(default="", max_length=100)
    detail_lines: list[str] = Field(default_factory=list, max_length=8)
    location_lines: list[str] = Field(default_factory=list, max_length=4)
    contacts: list[Contact] = Field(default_factory=list, max_length=8)
    sections: list[ContentSection] = Field(default_factory=list, max_length=8)
    cta_lines: list[str] = Field(default_factory=list, max_length=3)
    protected_copy: list[str] = Field(default_factory=list, max_length=120)

    @model_validator(mode="after")
    def protected_copy_must_be_displayed(self) -> "BasePosterContent":
        visible = "\n".join(self.display_strings())
        missing = [value for value in self.protected_copy if value and value not in visible]
        if missing:
            raise ValueError(f"Protected copy is not present in display content: {missing[:5]}")
        return self

    def display_strings(self) -> list[str]:
        excluded = {"content_type", "protected_copy"}
        payload = self.model_dump(mode="python", exclude=excluded)
        strings: list[str] = []

        def visit(value: Any) -> None:
            if isinstance(value, str):
                if value.strip():
                    strings.append(value)
            elif isinstance(value, dict):
                for nested in value.values():
                    visit(nested)
            elif isinstance(value, list):
                for nested in value:
                    visit(nested)

        visit(payload)
        return strings


class InformationContent(BasePosterContent):
    content_type: Literal[ContentType.INFORMATION] = ContentType.INFORMATION


class TournamentContent(BasePosterContent):
    content_type: Literal[ContentType.TOURNAMENT] = ContentType.TOURNAMENT
    short_name: str = Field(default="", max_length=80)
    organizer_tagline: str = Field(default="", max_length=140)
    categories: list[EventCategory] = Field(default_factory=list, max_length=6)


class CampContent(BasePosterContent):
    content_type: Literal[ContentType.CAMP] = ContentType.CAMP
    program_info: str = Field(default="", max_length=220)
    coach_heading: str = Field(default="", max_length=140)
    coach_bio: str = Field(default="", max_length=700)


class CoachingContent(BasePosterContent):
    content_type: Literal[ContentType.COACHING] = ContentType.COACHING


class LaneRentalContent(BasePosterContent):
    content_type: Literal[ContentType.LANE_RENTAL] = ContentType.LANE_RENTAL


PosterContent: TypeAlias = Annotated[
    InformationContent
    | TournamentContent
    | CampContent
    | CoachingContent
    | LaneRentalContent,
    Field(discriminator="content_type"),
]
POSTER_CONTENT_ADAPTER = TypeAdapter(PosterContent)


def parse_poster_content(payload: dict[str, Any]) -> PosterContent:
    return POSTER_CONTENT_ADAPTER.validate_python(payload)


def parse_editable_content(payload: dict[str, Any]) -> PosterContent:
    editable = dict(payload)
    editable["protected_copy"] = []
    return parse_poster_content(editable)


def protect_all_copy(content: PosterContent) -> PosterContent:
    payload = content.model_dump(mode="python")
    payload["protected_copy"] = list(dict.fromkeys(content.display_strings()))
    return parse_poster_content(payload)


class DesignTokens(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title_scale: float = Field(default=1.0, ge=0.88, le=1.12)
    body_scale: float = Field(default=1.0, ge=1.0, le=1.12)
    panel_opacity: float = Field(default=0.88, ge=0.72, le=0.96)
    spacing_scale: float = Field(default=1.0, ge=0.82, le=1.08)
    art_position_x: int = Field(default=50, ge=0, le=100)
    art_position_y: int = Field(default=50, ge=0, le=100)


class DesignSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: LayoutFamily
    density: Density
    composition: CompositionMode = CompositionMode.BALANCED
    color_mode: ColorMode = ColorMode.DARK
    font_preset: FontPreset = FontPreset.ATHLETIC
    style_intent: StyleIntent = StyleIntent.BOLD_ATTENTION
    # Optional so DesignSpec rows written before theming still validate.
    theme: ThemePack | None = None
    visual_treatment: VisualTreatment = VisualTreatment.HERO
    visual_intents: list[VisualIntent] = Field(default_factory=list, max_length=8)
    palette: Palette
    tokens: DesignTokens = Field(default_factory=DesignTokens)
    art_prompt: str = Field(min_length=40, max_length=1800)
    art_subject: str = Field(default="", max_length=500)
    art_focus: Literal["left", "center", "right"] = "right"
    width: int = Field(default=1080, frozen=True)
    height: int = Field(default=1350, frozen=True)
    min_body_px: int = Field(default=24, ge=24, le=36)
    safe_margin_px: int = Field(default=32, ge=24, le=80)


class AuditSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class AuditIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: AuditSeverity
    message: str
    field: str = ""
    value: str = ""


class Rect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    @property
    def area(self) -> float:
        return self.width * self.height


class InkKind(str, Enum):
    TEXT = "text"
    PANEL = "panel"
    IMAGE = "image"


class InkRect(Rect):
    kind: InkKind


class RegionGeometry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_id: str
    parent_id: str = ""
    depth: int = 0
    box: Rect
    ink_area: float = 0.0
    text_length: int = 0
    font_size: float = 0.0
    is_panel: bool = False
    is_art: bool = False
    is_leaf: bool = True

    @property
    def fill_ratio(self) -> float:
        area = self.box.area
        return self.ink_area / area if area > 0 else 0.0


class TextBackdrop(BaseModel):
    """Measured from a screenshot taken with all text hidden.

    This is the authoritative contrast measurement. The CSS-derived check in
    ``audit_render`` cannot see through translucent panels, so it reports the
    panel's own colour rather than what a reader actually sees.
    """

    model_config = ConfigDict(extra="forbid")

    region_id: str
    field: str = ""
    text_color: str = ""
    font_size: float = 0.0
    contrast_worst: float = 0.0
    contrast_median: float = 0.0
    luminance_p10: float = 0.0
    luminance_p50: float = 0.0
    luminance_p90: float = 0.0
    luminance_stdev: float = 0.0
    sample_count: int = 0


class PosterGeometry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: int = 1080
    height: int = 1350
    composition: CompositionMode = CompositionMode.BALANCED
    visual_treatment: VisualTreatment = VisualTreatment.HERO
    safe_margin_px: int = 32
    regions: list[RegionGeometry] = Field(default_factory=list)
    ink_rects: list[InkRect] = Field(default_factory=list)
    text_backdrops: list[TextBackdrop] = Field(default_factory=list)
    font_census: list[tuple[float, float]] = Field(default_factory=list)
    art: Rect | None = None


class MetricScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    raw: float
    score: float = Field(ge=0.0, le=1.0)
    weight: float = Field(default=1.0, ge=0.0)
    note: str = ""


class LayoutScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: float = Field(ge=0.0, le=1.0)
    weights_profile: str = ""
    metrics: list[MetricScore] = Field(default_factory=list)

    def metric(self, name: str) -> MetricScore | None:
        return next((item for item in self.metrics if item.name == name), None)


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    checks: dict[str, bool] = Field(default_factory=dict)
    issues: list[AuditIssue] = Field(default_factory=list)
    measured: dict[str, Any] = Field(default_factory=dict)
    protected_copy_matches: dict[str, bool] = Field(default_factory=dict)
    # Added in the measurement-foundation phase. Optional with a default so
    # project rows written before it existed still validate under extra="forbid".
    geometry: PosterGeometry | None = None
    score: LayoutScore | None = None


class PosterProject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: uuid4().hex)
    brand_id: str
    source_text: str = ""
    content: PosterContent
    design: DesignSpec | None = None
    render_mode: GenerationMode = GenerationMode.HYBRID
    status: ProjectStatus = ProjectStatus.DRAFT
    artwork_path: str | None = None
    html_path: str | None = None
    poster_path: str | None = None
    audit: ValidationReport | None = None
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

# Hybrid Cricket Poster Studio

A local one-page poster workflow for cricket academies, tournaments, coaching,
and lane rental. It has two generation modes:

- **Smart Hybrid (recommended):** Ideogram creates text-free cricket artwork;
  Playwright adds exact, editable typography. Use it whenever dates, prices,
  phone numbers, addresses, rules, or long copy must be correct.
- **Ideogram Full Poster:** Ideogram creates the artwork and typography together.
  The option is available only for light copy and always requires manual
  proofreading because generated text is not deterministic.

The studio first classifies the copy as spacious, compact, or dense. Spacious
projects use an art-forward composition, compact projects use a balanced
composition, and dense projects use an information-forward composition.
Ideogram-only mode is disabled when the poster exceeds its safe text limits.

Smart Hybrid also selects an artwork treatment:

- `hero` for spacious copy: one large full-canvas photograph
- `vignette` for compact or dense copy: one smaller generated intent photograph
  plus transparent semantic PNG icons attached to matching list items

The intent finder uses registered concepts such as strength, coordination,
learning, fitness, batting, bowling, coaching, registration, and facilities.
It does not rewrite poster copy.

## Visual intent

Visual intent is a first-class input alongside the copy: the same information can
be rendered as eight different looks. Choose one of `bright_vibrant`,
`minimal_clean`, `premium_elegant`, `bold_attention`, `professional_clean`,
`youthful_energetic`, `playful_fun`, or `modern_sleek`.

An intent never replaces the brand's colours — the accent hue is preserved
exactly. What changes is how those colours are *deployed*: how dominant the
accent is, how much it tints the surfaces, the typeface and its weight and
tracking, corner radius, border and shadow weight, whitespace, and the
decoration layer. Every generated colour that carries text is pushed through a
contrast solver, so a theme cannot be produced that fails the 4.5:1 audit gate.

Case is deliberately not themeable. Chrome reports `text-transform` through
`innerText`, so restyling copy to uppercase would both break the protected-copy
audit and silently alter the wording the academy supplied.

Each intent selects one of eight bundled typefaces — athletic (Anton), condensed
(Bebas Neue), impact (Archivo Black), modern (Space Grotesk), geometric (Outfit),
rounded (Poppins), editorial (Playfair Display), friendly (Fraunces) — which can
be overridden. Fonts are self-hosted woff2 under `assets/fonts` and are never
fetched from a CDN at render time; see `assets/fonts/NOTICE.md` for licensing.
Rendering waits on `document.fonts.ready` so a screenshot can never capture
fallback metrics. Light and dark rendering are both supported.

The hybrid pipeline is:

1. GPT-5.4 extracts pasted details into validated structured content.
2. A constrained planner selects one of six registered single-page layouts.
3. Ideogram 4 generates text-free cricket artwork using a structured JSON prompt.
4. Playwright renders exact factual copy through HTML and CSS.
5. A deterministic audit checks copy, overflow, margins, type size, contrast,
   logo loading, and 1080 × 1350 dimensions.

The studio never creates a carousel. If all required copy cannot fit legibly at
the 24px body-text minimum, it identifies the overflowing fields and asks for a
copy revision.

## Install and run

```powershell
uv sync --all-groups
uv run cricket-posts serve
```

Open `http://127.0.0.1:8000`. The local workflow is:

`brand → paste details → review copy and text-load assessment → choose mode → generate → validate → export`

Copy `.env.example` to `.env` and add `OPENAI_API_KEY` and
`IDEOGRAM_API_KEY` for live extraction, planning, artwork, and optional visual
critique. API keys stay in the server process and are never sent to the browser.

## CLI

Generate from a structured fixture without API calls:

```powershell
uv run cricket-posts generate --input fixtures/svats-cup.json --offline
```

Generate with GPT-5.4 and Ideogram:

```powershell
uv run cricket-posts generate --input fixtures/summer-camp.json --critic
```

Generate a light Smart Hybrid poster with a modern font:

```powershell
uv run cricket-posts generate --input fixtures/foundation-program-houston.json --theme light --font modern
```

Generate a light-copy poster entirely in Ideogram:

```powershell
uv run cricket-posts generate --input fixtures/information.json --ideogram-only
```

Generate with an explicit visual intent:

```powershell
uv run cricket-posts generate --input fixtures/summer-camp.json --offline --intent playful_fun
```

Score every fixture offline and write a calibration contact sheet:

```powershell
uv run cricket-posts score --all-fixtures
```

Sweep every visual intent across every fixture (128 posters across both colour
modes, no API calls):

```powershell
uv run cricket-posts score --intents all
uv run cricket-posts score --intents all --theme light
```

This renders each fixture without calling any API, records the deterministic
layout score alongside the usual audit, and writes `output/calibration/index.html`
plus `scores.json`. The contact sheet ranks the posters by score so the ranking
can be compared against human judgement.

Validate or export an existing project:

```powershell
uv run cricket-posts validate --project PROJECT_ID
uv run cricket-posts export --project PROJECT_ID
```

The earlier proof-of-concept commands remain available:

```powershell
uv run cricket-posts sample
uv run cricket-posts live --request "Create three July posts for our academy."
```

## Layout families

- `announcement_hero`
- `tournament_registration`
- `tournament_category_grid`
- `summer_camp`
- `coaching_services`
- `lane_rental`

Density variants adjust spacing, artwork prominence, and hierarchy while
keeping hybrid body text at or above 24px. GPT may only select registered
layouts and bounded design tokens. In Smart Hybrid mode, factual typography
always remains outside the generated artwork.

For ordinary pasted text, extraction fails if GPT changes, invents, or omits a
source line. The application never asks GPT to polish grammar or improve the
user's prompt. Only the separate text-free artwork prompt is written by the
system.

## Local API

FastAPI exposes:

- brands: `GET/POST /api/brands`
- extraction: `POST /api/extract`
- projects: `GET/POST /api/projects`
- copy editing: `PUT /api/projects/{id}/content`
- generation: `POST /api/projects/{id}/generate`
- rerendering: `POST /api/projects/{id}/rerender`
- new artwork: `POST /api/projects/{id}/regenerate-art`
- validation: `POST /api/projects/{id}/validate`
- export: `GET /api/projects/{id}/export`

Interactive OpenAPI documentation is available at `/docs`.

## Persistence and export

Project and job state is stored in `studio.db`. Completed artwork and render
stages are reused after restart. A project ZIP contains:

- final PNG
- editable project JSON
- `DesignSpec`
- source artwork
- rendered HTML
- generation metadata, prompts, and seed when available
- validation report

## Tests

```powershell
uv run pytest
```

Normal tests mock or avoid paid providers and render all six fixtures through
the installed Chrome or Edge browser. Paid live smoke tests are opt-in:

```powershell
$env:RUN_LIVE_AI_TESTS = "1"
uv run pytest -m live
```

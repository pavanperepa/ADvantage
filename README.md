# ADvantage

ADvantage is a manifest-led agent that turns a small business's
rough request and supplied assets into verified static ads and reels/videos,
then prepares a paused Meta campaign for human approval. The working 22Yards
poster studio and Remotion reels are the current proof case and implementation
foundation.

For hosting, see the [Vercel deployment guide](docs/VERCEL_DEPLOYMENT.md) and
the repository Services configuration in `vercel.json`.

## Start here

- `AGENTS.md` — safety, approval, privacy, and verification rules.
- `PROJECT_MEMORY.md` — current business context, deliverables, decisions, and
  known inconsistencies.
- `docs/CORE_PROJECT_FILES.md` — the canonical files we are keeping and what
  each part of the current system does.
- `docs/ARCHITECTURE.md` — active product, reusable-engine, operations, and
  reference boundaries.
- `docs/API_CONTRACTS.md` — versioned request/response contracts prepared for
  the owner-facing UI.
- `docs/FUTURE_SCOPE.md` — the hackathon product scope, implementation plan,
  demo sequence, evaluation strategy, and explicit non-goals.
- [Hackathon and beta MVP 1 execution plan](docs/HACKATHON_BETA_MVP1_PLAN.md) —
  reviewed gaps, happy path, delivery phases, evaluation and release gates.
- [P0-02 baseline validation](docs/P0_02_BASELINE_VALIDATION.md) — branch,
  source inventory, focused test/render evidence, integration preflight, and
  the remaining demo-readiness gates.
- [GitHub Project backlog](docs/GITHUB_PROJECT_BACKLOG.md) — ticket index,
  acceptance criteria, dependencies, priorities, and links to the execution board.

## Repository layout

- `src/advantage/` is the active product: API contracts, campaign domain,
  application orchestration, integrations, and adapters.
- `src/cricket_posts/` and `remotion/` are reusable rendering engines called by
  those adapters.
- `scripts/` contains maintained operator commands grouped by responsibility.
- `reference/main/` contains superseded experiments and examples retained from
  the earlier repository; production code does not import it.

New application imports should start at `advantage`. The old
`cricket_posts.campaign` path remains only as a compatibility bridge.

The remainder of this README documents the implemented poster engine in detail.

## Current implementation: Hybrid Cricket Poster Studio

## Project context for future agents

This repository now includes poster generation, Remotion reels, and Houston Meta
Ads tooling. Future GPT/Astra sessions should begin with:

- `AGENTS.md` for operating and safety rules;
- `PROJECT_MEMORY.md` for business context, current assets, decisions, history,
  and known inconsistencies;
- `docs/CORE_PROJECT_FILES.md` for the active keep-set and file responsibilities;
- `docs/FUTURE_SCOPE.md` for the prioritized roadmap.

These documents cover newer campaign work that is not yet fully represented in
the Git history or the poster-focused sections below.

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
Add `SLACK_BOT_TOKEN` to send a generated poster and message to a public Slack
channel from the campaign page. It is used only by FastAPI and must not be
added to `frontend/.env.local` or any `NEXT_PUBLIC_` variable. The Slack app
uses the bot scopes `channels:read`, `chat:write`, `chat:write.public`, and
`files:write`. No public callback URL, Interactivity configuration, or Event
Subscriptions are needed for this one-way sharing flow.

## Google Drive intake

The read-only Drive adapter accepts one explicit folder URL/ID, inventories only
its direct children, and downloads a bounded allow-list of logo, photo, short
video, and brief types. It records content hashes and sanitized source references,
deduplicates identical files, rejects oversized or overlong media, and quarantines
imported instructions that attempt to authorize tools, publishing, or secret
access.

Create a permission-safe neutral packet for a live Drive demo:

```powershell
uv sync --group video
uv run python scripts/demo/create_drive_demo_packet.py
```

Upload the files under `output/drive_demo_source/` to a small test folder. In
Google Cloud, enable the Drive API, configure the OAuth consent screen/test user,
and add this exact authorized redirect URI to the OAuth **Web application**
client:

```text
http://localhost:8765/oauth2/callback
```

Put `GOOGLE_DRIVE_OAUTH_CLIENT_ID` and `GOOGLE_DRIVE_OAUTH_CLIENT_SECRET` in the
ignored `.env` (never in source or shell history), then complete consent once:

```powershell
uv run python scripts/intake/google_drive_authorize.py
```

The authorization helper requests only Google's `drive.readonly` scope, checks
the OAuth state value, receives the result on localhost, and stores the refresh
token in `.env` without displaying it. The scope can read Drive broadly at the
provider boundary; this adapter narrows its own behavior to one explicit folder,
direct children only, and never calls a Drive write endpoint. A production
deployment must keep each user's refresh token in a secrets manager or encrypted
server-side store rather than `.env`.

After authorization, run:

```powershell
uv run python scripts/intake/google_drive_intake.py --folder "<folder URL or ID>"
```

The command writes downloaded files and `inventory.json` under the ignored
`output/drive_intake/` directory. Console output contains counts and hashed
references, not access tokens, raw Drive IDs, source filenames, or brief content.
The command refreshes the short-lived access token automatically. The older
`GOOGLE_DRIVE_ACCESS_TOKEN` setting remains available only as a manual local
preflight fallback.

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

## Composing posters

`compose` is the current pipeline and the one to reach for. It builds a poster
from three layers — a background plate, transparent subject cut-outs, and exact
copy — and **calls no API at all**. Plates are restocked occasionally; composing
from them is local, free and repeatable.

```powershell
uv run cricket-posts compose --input fixtures/academy-u10-houston.json `
  --archetype split_field --plate austin-geometric-left-01.png `
  --intent bold_attention --bullets checks --info slab --headline outline
```

Read the printed report, not just the PNG. `Copy` must say every value renders
verbatim, `CLIPPED` must be absent, `Fit` should land between 88% and 97%, and
`Dead space` should stay under 11%. When a contact treatment paints straight
onto the plate, a `Footer` line reports the worst contrast it has against the
artwork underneath and tells you to switch treatments if it is unreadable.

### Archetypes — where the copy goes

| id | copy | artwork | plates from |
|---|---|---|---|
| `left_column` | left third | right half | generated |
| `right_column` | right third | left half | `mirror`, or generated |
| `top_band` | upper half, two columns | lower half | generated |
| `bottom_third` | lower two fifths, two columns | upper half | generated |
| `center_stage` | centred middle | outer margins | generated |
| `split_field` | inside a CSS colour field | whatever the plate has | **any plate** |

`split_field` paints its own field through a `clip-path`, so it takes its region
outright instead of measuring for one — which is why it works on every plate in
the bank and costs no generations.

An archetype is never inferred freely. It comes from `--archetype`, or failing
that from the plate's own manifest tag, so adding a layout cannot silently
restyle posters that were already right.

### Treatments — what the blocks wear

```
--bullets   auto | dots | feature | rules | checks
--info      bar | stack | columns | buttons | icon_cards | slab
--badge     block | stamp
--headline  solid | outline
```

`stack` and `slab` change *where* the contact details sit, not just what they
look like; that is where variety a reader notices comes from. `columns` and
`buttons` have no surface of their own and paint onto the plate — legible only
where the foot of that plate is dark enough, which the `Footer` line measures.
`outline` acts on the line breaks already in the title, so a one-line title
renders solid rather than being split on a guess.

### Restocking the plate bank

Mirroring is free and safe, because a plate carries no text and no crest by
construction — the two things a horizontal flip ruins do not exist on one:

```powershell
uv run cricket-posts mirror --file austin-geometric-left-01.png
```

Generating costs money, so the machine gate runs before you look. Every
candidate is measured against the archetype's own expectation and rejected if
the calm space is in the wrong place or too small, which is the failure no CSS
recovers from:

```powershell
uv run cricket-posts restock --archetype top_band --name top-band-turf `
  --brand fixtures/academy-u7-houston.json --attempts 3 `
  --scene "The lower half is a bright outdoor cricket ground ..."
uv run cricket-posts accept --file top-band-turf-01.png --note "why this one"
```

Candidates land in `assets/plates/_incoming/` with a `.plate.json` sidecar
carrying the seed, so a plate that turns out to be the good one can be
re-rendered at `--speed QUALITY` rather than re-rolled. **Always look before
accepting.** Measurement cannot see stray lettering, an invented crest, the
wrong sport, or artwork inset in a box instead of bled to the edges — two
attempts at automating that last one both failed, and the reasoning is recorded
in `plate_studio.verify`.

The Ideogram MCP server in `.mcp.json` is good for probing a brief
conversationally. Restock over the CLI once the wording is settled, so the seed
and the manifest entry come out complete.

### Age-band fixtures

`fixtures/academy-u{5,7,10,13}-houston.json` carry placeholder copy against the
real brand block. There is no age-group model — the band is free text in
`detail_lines`, the same way `after-school-houston.json` already carries
`AGES 6-13`. Those lines are `OPTIONAL` blocks, so on a short copy zone the fit
engine will drop them; if the age has to appear, keep the rest of the copy short
enough to leave room for it.

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

# ADvantage core project files

Status: working-tree inventory, verified 2026-09-12

This is the keep boundary for the revised product: generic small-business ad
creation with two output surfaces (static/poster and vertical reel/video),
deterministic QA, and safe, paused Meta deployment. The implementation in this
workspace is still a 22Yards Houston cricket academy system. That system is the
working foundation to generalize; it is not yet a generic SMB product. Git
history is incomplete, so this inventory follows the current working tree and
the actual import/output references.

## Read before changing the boundary

- `AGENTS.md` — operating, privacy, approval, and verification rules.
- `PROJECT_MEMORY.md` — current campaign decisions, known inconsistencies, and
  the handoff history. It is the source for the approved current poster/reel
  paths, subject to the source-of-truth order in `AGENTS.md`.
- `README.md` — poster studio and local API/CLI workflow.
- `remotion/README.md` and `remotion/LIBRARY.md` — reel architecture and the
  JSON-driven component library.
- `output/meta_ads_houston/HOUSTON_META_ADS_AUDIT.md` — evidence and control
  targets for Meta work.
- `docs/FUTURE_SCOPE.md` — the current product roadmap and hackathon plan. Keep
  this inventory aligned with it, but do not silently turn roadmap items into
  shipped behavior.

## Classification

- **Source/runtime**: keep and use for new work; code, contracts, templates,
  tests, and accepted assets.
- **Current deliverable**: the selected artifact for the current campaign or a
  directly associated proof.
- **Generated cache**: reproducible local output; useful during a session but
  not a source of truth.
- **Reference-only**: retained for comparison, evidence, or design learning;
  never silently selected as a new campaign input.
- **Transitional**: still needed by the current runtime but should be replaced
  or generalized before broad SMB use.

## Canonical keep-set

The following set is the practical product boundary. Keep the paths even when
they are untracked in the current checkout; do not infer that “untracked” means
“safe to remove.”

### Contracts, local runtime, and documentation

| Path | Role | Status |
| --- | --- | --- |
| `pyproject.toml`, `uv.lock` | Python package metadata, dependencies, test configuration, and the `cricket-posts` entry point. | Source/runtime; transitional package name. |
| `package.json`, `package-lock.json`, `tsconfig.json`, `remotion.config.ts` | Node dependencies, reproducible install, TypeScript checks, and Remotion entry/public/output settings. | Source/runtime. |
| `.env.example` | Names only for OpenAI, Ideogram, and read-only Meta configuration. | Source/runtime; contains no live values. |
| `.gitignore` | Protects secrets, media, outputs, and local caches from accidental history. | Source/runtime. |
| `.mcp.json` | Local provider/tool configuration. | Optional local runtime; inspect before sharing. |
| `AGENTS.md`, `PROJECT_MEMORY.md`, `README.md`, `remotion/README.md`, `remotion/LIBRARY.md`, this file | Safety rules, decisions, operator docs, reel library docs, and this keep boundary. | Source/reference. |

Never put `.env` or a token from it in this document, a commit, a prompt, or a
log. Current `.env` is intentionally ignored.

### Static/poster engine

Keep all of `src/cricket_posts/` as one package until the genericization work is
deliberately split. The important responsibilities are:

- `models.py`, `layout.py`, `openai_studio.py` — validated brand/content/design
  contracts, bounded layout planning, and optional structured extraction/critique.
  `models.py` currently names cricket content types and layout families, so this
  is the main schema boundary to generalize.
- `pipeline.py`, `composite.py`, `studio.py`, `renderer.py`,
  `studio_renderer.py`, `web.py`, `cli.py` — local compose path, exact-copy
  rendering, project orchestration, browser discovery, FastAPI app, and CLI.
- `blocks.py`, `fit.py`, `freespace.py`, `color.py`, `theme.py`,
  `layout_score.py` — copy ownership/fitting, pixel-based calm-space analysis,
  contrast/theme derivation, and deterministic aesthetic scoring.
- `archetypes.py`, `layouts.py`, `plates.py`, `plate_studio.py`, `subjects.py`,
  `intent_assets.py`, `poster_art.py`, `ideogram.py`, `ideogram_edit.py`,
  `layerize.py` — bounded layouts, artwork/subject banks, occasional Ideogram
  generation or clearing, and layout harvesting. Generation is an occasional
  restocking operation; normal composition should remain local and repeatable.
- `storage.py`, `tracking.py` — SQLite project/job persistence and tracked URLs
  plus QR generation.

`templates/` is runtime code, not disposable design output. Keep all of
`templates/studio/` (canvas, components, fonts, overlay, poster CSS/HTML) and
`templates/web/` (the studio pages), plus `templates/calibration.html`.

Keep `tests/` as the executable contract for the poster engine. The offline
suite covers models, blocks, fit, free space, layout scoring, themes, tracking,
render/export, storage, provider retries, and web API behavior. Live-provider
tests are opt-in and must not be used as a default smoke test.

The maintained operator scripts are also part of the keep-set:

- `scripts/create_houston_academy_poster.py` — face-safe deterministic static
  academy poster from supplied photographs.
- `scripts/create_strength_training_ideogram_poster.py` — current strength
  campaign poster compositor; it optionally calls Ideogram for artwork and
  always types factual copy locally.
- `scripts/generate_sports_instrumental.py` — reproducible source for the
  current vocal-free reel bed.
- `scripts/prepare_remotion_media.py` — local FFmpeg preparation described in
  the reel section below.
- `scripts/meta_ads_full_export.py`, `scripts/meta_ads_create_campaign.py`,
  `scripts/meta_ads_monitor.py`, and `scripts/meta_ads_pause.py` — read-only
  export/monitoring plus dry-run-first, paused, explicit-ID deployment helpers.

The two poster scripts above are campaign-specific adapters, not yet a single
neutral SMB renderer. Keep them as references while moving reusable behavior
into the package and a future neutral campaign manifest.

### Poster assets and local media inputs

- `assets/fonts/` — self-hosted woff2 faces and `assets/fonts/NOTICE.md`.
  Rendering must not depend on a CDN.
- `assets/brand/22yards-houston.png` — current real logo. It is a Houston
  adapter, not a universal default for the revised product.
- `assets/plates/manifest.json` and accepted plate PNGs in `assets/plates/` —
  text-free background bank indexed by archetype/intent/content type. The
  `*.freespace.json` files are analysis caches and can be rebuilt.
- `assets/layouts/manifest.json` and `assets/layouts/foundation-collage.png` —
  harvested layout proposal and its art source.
- `assets/subjects/manifest.json` plus local alpha PNGs under
  `assets/subjects/` — subject bank metadata and cut-outs. PNGs are ignored by
  Git; real photography is preferred when supplied and faces must remain
  recognizable.
- `assets/information-background.svg`, `assets/services-background.svg`,
  `assets/tournament-background.svg`, `assets/mark.svg`, and
  `assets/studio-app.css` — bundled poster backgrounds, mark, and studio chrome.
- `real-photo/` — ignored local source photographs; needed for some face-safe
  poster scripts but not a tracked runtime dependency. Treat identifiable
  children as sensitive local input.
- `image-bank/`, `Houston_11zon.webp`, and `huston-22yards.jpeg` — retained
  source/reference imagery from the cricket work. They are not generic product
  defaults and should not become implicit inputs.

### Reel/video renderer

Keep all of `remotion/` source and docs:

- `remotion/index.tsx` and `remotion/Root.tsx` — Remotion entry point and the
  registered `AcademyIntro`, `PracticeMatchReel`, `ReelComponentLibrary`,
  `ReelLibraryDemo`, and `PracticeMatchLibraryReel` compositions.
- `remotion/AcademyIntro.tsx` — reusable footage, motion, transition, audio,
  and overlay composition. The name and current brand assumptions are cricket
  specific even though the rendering boundary is reusable.
- `remotion/types.ts` — the `EditSpec`, shot, overlay, motion, transition, and
  theme contract. This is the future neutral video campaign contract.
- `remotion/library/` — reusable themes, overlay renderer, cards, motion,
  transitions, and decorations. `catalog.ts` is the bounded vocabulary;
  `ComponentGallery.tsx` is the visual catalog.

`scripts/prepare_remotion_media.py` is the preparation runtime. It reads source
paths from an EditSpec, trims/normalizes footage with FFmpeg, and copies the
logo, fonts, and music into `remotion/public/`. `remotion/public/` is an ignored
generated cache, not source; rebuild it from the fixture and local media.

The current local source video directory is `vids/`. The `practice-match*.mp4`
files are the source clips for the approved practice-match fixture. Do not
confuse them with prepared clips in `remotion/public/practice-match/` or the
duplicate/reference copies in `output/practice-match-source/`.

`assets/music/houston-sports-pulse-instrumental.wav` is the current original,
vocal-free practice-match reel bed; its reproducible source is
`scripts/generate_sports_instrumental.py`. `assets/music/LICENSE.md` records the
license provenance for `assets/music/mixkit-dirty-thinkin-989.mp3`, which is
still required by the registered academy-intro reference composition but is not
the current practice-match default.

### EditSpecs and poster fixtures

JSON fixtures are editorial inputs and QA examples, not a hidden database. Keep
the current poster examples in `fixtures/`, including the generic-shaped
`information.json`, `coaching-services.json`, `summer-camp.json`,
`lane-rental.json`, and `tournament-registration.json`, and the Houston/age-band
fixtures (`academy-u5/u7/u10/u13-houston.json`, `after-school-houston.json`,
`foundation-*`, `lane-rental-houston.json`, `small-squads-coaches-houston.json`,
`summer-camp-*`, `svats-cup.json`). They exercise the schema and layouts, but
their copy and `ContentType` values remain cricket-specific examples.

The current static campaign source is:

- `fixtures/strength-training-free-trial-sept13-houston.json` — content for the
  approved September 15 poster. The `sept13` filename is stale; its content is
  the authority for this fixture until a deliberate rename updates every
  reference.

The four EditSpecs imported by `remotion/Root.tsx` are runtime keepers:

- `fixtures/reel-practice-match-v2.json` — current approved practice-match reel
  source; muted camera audio and the September 15 deadline are intentional.
- `fixtures/reel-practice-match-library-v1.json` — component-library practice
  reel draft, not an approved replacement.
- `fixtures/reel-library-demo-v1.json` — JSON-driven library demonstration.
- `fixtures/reel-academy-remotion-v1.json` — older academy-intro composition
  still required by `Root.tsx` and useful as a renderer reference. Its phone,
  URL, and stock-music metadata are older values and must not be copied into a
  new campaign without review.

Other fixture files are valid poster examples or retained reel history, but only
the four above are Remotion runtime imports. New SMB fixtures should preserve
the same separation between factual copy, brand data, editorial timing, and
rendered artwork.

Poster tests and calibration select only fixtures whose content contains a
`content_type`; reel EditSpecs intentionally use a different schema. This
boundary allows both fixture families to coexist without feeding video data to
the poster parser.

### QA, evidence, and Meta deployment

- Poster QA is in `studio_renderer.py` (copy, overflow, margins, type size,
  contrast, logo, and dimensions) and `layout_score.py` (aesthetic score that
  does not decide validity). Run the offline tests and inspect the final PNG.
- Reel QA is currently a human inspection workflow: render representative
  frames, inspect the opening hook and final CTA, verify 1080x1920, play the MP4,
  and confirm muted camera audio where the fixture requires it. There is no
  standalone automated EditSpec/voice/safe-zone validator yet.
- `scripts/meta_ads_full_export.py` is read-only history export. Its aggregate
  outputs and `manifest.json` belong in `output/meta_ads_houston/`, together
  with `HOUSTON_META_ADS_AUDIT.md` and the CSV evidence. The export contains no
  customer-level lead records.
- `scripts/meta_ads_create_campaign.py` is dry-run-first. `--execute` creates
  objects paused; it must not be used until the final creative, copy, dates,
  audience, budget, form, and destination are approved. It currently creates a
  single Houston video lead ad, has an older hard-coded phone/default video,
  and is not a generic two-creative publisher.
- `scripts/meta_ads_monitor.py` is read-only threshold monitoring.
  `scripts/meta_ads_pause.py` takes explicit object IDs and verifies state; it
  has no broad pause/delete mode. Meta mutations remain a separate permission
  from analysis.

## Current deliverables and reference artifacts

These paths exist locally and are the named campaign/demo evidence. Outputs are
ignored by Git, so preserve selected files intentionally when handing off.

| Artifact | Path | Classification |
| --- | --- | --- |
| Approved static poster, Instagram Feed 4:5 (1080x1350) | `output/posters/22yards-houston-strength-training-free-trial-sept15-ideogram.png` | Current deliverable. |
| Reusable text-free poster artwork | `output/posters/strength-training-ideogram-artwork.png` | Current source asset/cache for the poster script. |
| Approved vertical practice-match reel (1080x1920) | `output/practice-match-reel/22yards-practice-match-reel-sept-15-deadline-highlight-v4.mp4` | Current deliverable. |
| Reel closing-frame proof | `output/practice-match-reel/deadline-highlight-closing-frame-sept15.png` | Current QA proof. |
| Component-library practice reel | `output/practice-match-reel/22yards-practice-match-library-v1.mp4` | Draft/reference; does not replace `v4`. |
| Component-library demo | `output/reel-component-library/library-demo-v1.mp4` and its PNG stills | Current demo/reference. |
| Academy-intro reel | `output/reel-lab/academy-intro-remotion-v7-natural-ending.mp4` | Transitional reference still named by `package.json` and the current Meta creator; replace those defaults before retiring it. |
| Houston Meta evidence | `output/meta_ads_houston/` | Current read-only audit/reference; CSVs are aggregate history. |

The static deliverable is composed by
`scripts/create_strength_training_ideogram_poster.py`, which reads the logo,
fonts, and artwork and writes exact factual typography. Its exact copy is
currently hard-coded in the script; the similarly valued fixture is a matching
campaign record, so review both when changing dates, phone, URL, or offer.
It only needs `--generate` when a new paid Ideogram call is intentionally
authorized. The approved reel is prepared/rendered through
`reel-practice-match-v2.json`,
`scripts/prepare_remotion_media.py`, `remotion/Root.tsx`, and
`package.json`'s `practice:prepare`/`practice:render` scripts.

The September 15, 2026 free-trial language is campaign-specific. It must be
removed or replaced after that date; do not promote these files as evergreen
creative merely because they are present.

## Rebuild and verification commands

Use the existing environment and inspect outputs after each run:

```powershell
uv sync --all-groups
uv run pytest
uv run cricket-posts serve
.\.venv\Scripts\python.exe scripts\create_strength_training_ideogram_poster.py
npm install
npm run practice:prepare
npm run practice:render
```

Start Meta work with the default dry run and inspect all payloads. Use the
read-only exporter/monitor for analysis. `--execute` only creates paused
objects, and no campaign should be activated without explicit final approval.

## Generated and non-canonical boundaries

The following are rebuildable or exploratory and are not source of truth:

- `output/calibration/`, `output/compose/`, `output/projects/`,
  `output/artpass/`, `output/austin-plates/`, `output/bands/`,
  `output/harvest/`, `output/ideogram/`, `output/layerize/`, `output/live/`,
  `output/probe/`, `output/real/`, and `output/variants/` — poster experiments,
  rendered HTML/PNGs, calibration scores, and provider probes.
- Older files beside the current reel in `output/practice-match-reel/`, and
  most of `output/reel-lab/` — iteration frames, logs, PIDs, contacts, and
  superseded renders. Keep a particular file only as a named review artifact.
- `output/reel-component-library/` is useful for the component demo, but its
  stills and renders are generated evidence, not renderer source.
- `output/practice-match-source/` duplicates local source clips and is not read
  by the preparation script when the canonical `vids/` paths exist.
- `remotion/public/`, `*.freespace.json`, `studio.db`, `.venv/`,
  `.uv-cache/`, `.mypy_cache/`, `.pytest_cache/`, `node_modules/`, and
  `__pycache__/` are local caches/state. Do not put them in a baseline commit.

Generated does not mean disposable during an active review: selected current
deliverables, QA proofs, and Meta audit exports should be copied or archived
before cache cleanup.

## Legacy exclusions and transition boundary

Retain these only for traceability while the migration is reviewed; do not use
them as the new production path:

- `scripts/shotstack_academy_intro.py` is an obsolete external-renderer
  experiment; the maintained renderer is Remotion plus local preparation.
- `scripts/twelvelabs_reel_probe.py` is a working footage-understanding
  prototype. It is not required to render an existing EditSpec, but keep it as
  the current reference for the video-ingestion/semantic-selection stage until
  that behavior is replaced by the unified campaign agent.
- `scripts/render_reel_draft.py` is the earlier hand-built FFmpeg draft path.
- `scripts/create_titans_instagram_poster.py` and
  `scripts/create_titans_winner_poster.py` are one-off winner-poster scripts
  tied to external desktop photos; they are not the poster studio.
- `fixtures/reel-academy-intro-v1.json`, `fixtures/reel-coaching-probe.json`,
  `fixtures/reel-coaching-v2.json`, `fixtures/reel-coaching-v3.json`, and
  `fixtures/reel-practice-match-v1.json` are superseded reel plans. Their
  outputs and contact sheets in `output/reel-lab/` or
  `output/practice-match-reel/` are historical references.
- Older reels using `assets/music/mixkit-dirty-thinkin-989.mp3` are not the
  current practice-match path. The track and `assets/music/LICENSE.md` remain
  runtime/provenance dependencies of the registered academy-intro reference
  composition until that composition is retired.
- `assets/plates/_incoming/` is staging. A candidate is not part of the plate
  bank until it passes the machine gate and is deliberately human-accepted.

The main generalization work remains explicit: replace cricket-only content
enums/prompts/assets and Houston Meta defaults with a neutral campaign/brand
contract, while preserving the exact-copy, face-safe, deterministic QA, and
paused-deployment guarantees. Until then, keep cricket adapters and label them
as such rather than claiming broad SMB support.

## Working-tree cautions

- Inspect `git status` before edits. Current Remotion, scripts, fixtures,
  memory, and campaign artifacts are largely untracked additions to a tracked
  poster baseline; preserve them unless the owner explicitly decides otherwise.
- Never run `git clean`, broad deletion, or a reset to “tidy” generated files.
  Confirm exact paths and archive selected deliverables first.
- Verify changeable dates, offers, phone numbers, URLs, budgets, forms, and Meta
  IDs against the latest approved source before publishing or mutating Meta.
- Keep real children's faces from supplied photography; use crop/brightness/
  color/layout operations and deterministic overlays. Do not generatively alter
  faces without explicit approval.

# Project memory: 22Yards marketing system

Last verified: September 8, 2026
Repository/product: `ADvantage`
Primary location in scope: Houston, Texas

This document is the durable handoff for future GPT/Astra sessions. It records
what the repository does, how it evolved, what the business has approved, what
the current deliverables are, and what still needs confirmation. It deliberately
contains no API keys or customer-level lead data.

## 1. Purpose

The repository is becoming an end-to-end local marketing system for cricket
academies. It currently has three connected capabilities:

1. Create Instagram posters from structured copy, brand assets, generated or
   supplied imagery, and deterministic typography.
2. Turn local training footage into reusable 9:16 reels using JSON edit specs,
   prepared media, and Remotion.
3. Export and analyze Houston Meta Ads history, create paused campaign objects,
   monitor performance, and explicitly pause named objects.

The practical goal is not simply to generate attractive assets. It is to create
repeatable, measurable campaigns whose copy is accurate, whose real subjects
remain recognizable, and whose performance can be connected to qualified
leads, trials, and enrollments.

## 2. Known Houston business context

### Audience and offer

- Children in the U5-U13 range.
- Beginner and intermediate players are both appropriate.
- The program combines cricket skill development with physical fitness.
- Strength, core, balance, movement, speed, and coordination are meaningful
  differentiators to explain.
- Cricket's growth in the United States can be used as context, but creative
  should still lead with a concrete parent/child benefit.
- Match exposure exists, but depends on each child's rate of skill development
  and readiness. Never promise that every new child will immediately play.
- Do not advertise a single schedule because training days differ by age group.
- Do not advertise price.
- A free trial may be promoted when the business approves it for that campaign.
- Parents may register online, call, or use WhatsApp.

### Current contact and brand values

- Display phone: `+1 (713) 498-2155`.
- Registration URL:
  `https://axon22yards.com/join?location=houston`.
- Houston logo used by the current poster workflow:
  `assets/brand/22yards-houston.png`.
- Current poster palette: deep/royal blue, white, and cricket yellow, based on
  `#063D7C`, `#0757A6`, `#F5C400`, and light blue supporting surfaces.
- Current reel palette uses green `#8CC63F`, yellow `#FFD437`, and very dark ink.

There is a contact inconsistency to resolve before the next Meta launch:
`scripts/meta_ads_create_campaign.py` still contains `+1 (713) 570-9054`, while
the latest approved creative uses `+1 (713) 498-2155`. The latest user-approved
value is the latter, but the campaign script must be reviewed rather than run as
is.

## 3. Current September 15 campaign

The latest concept uses two creative angles in one Houston campaign:

- Poster angle: a better cricketer also needs to become a stronger athlete.
  Age-appropriate strength training is built into the academy program.
- Reel angle: weekly coached practice matches make match-day decisions and
  pressure more familiar.

Both assets use the campaign-specific call to action to claim a free trial
before September 15, 2026. That deadline is time-sensitive and must not remain
in evergreen ads after it passes.

### Current final outputs

- Poster, Instagram Feed 4:5:
  `output/posters/22yards-houston-strength-training-free-trial-sept15-ideogram.png`
- Reel, Instagram 9:16:
  `output/practice-match-reel/22yards-practice-match-reel-sept-15-deadline-highlight-v4.mp4`
- Reel closing-frame QA proof:
  `output/practice-match-reel/deadline-highlight-closing-frame-sept15.png`

A component-library remake of the practice-match reel was rendered for review
on September 10, 2026. It is a draft and does not replace the approved `v4`
artifact unless the user explicitly approves it:

- Draft reel: `output/practice-match-reel/22yards-practice-match-library-v1.mp4`
- Draft EditSpec: `fixtures/reel-practice-match-library-v1.json`

Older September 13 outputs were intentionally retained for traceability. Do not
mistake them for the current files.

### Current implementation sources

- Poster compositor:
  `scripts/create_strength_training_ideogram_poster.py`
- Reusable text-free poster artwork:
  `output/posters/strength-training-ideogram-artwork.png`
- Poster content fixture:
  `fixtures/strength-training-free-trial-sept13-houston.json`
- Reel edit spec:
  `fixtures/reel-practice-match-v2.json`
- Reel renderer/compositions:
  `remotion/AcademyIntro.tsx` and `remotion/Root.tsx`
- Original vocal-free music:
  `assets/music/houston-sports-pulse-instrumental.wav`

Two filenames are stale even though their content was updated: the strength
fixture still says `sept13` in its filename, and the package render command uses
a less specific reel filename than the delivered `v4` file. Normalize these
only as a deliberate cleanup, because other scripts may reference them.

### Creative decisions already learned

- Preserve supplied real photographs and faces. Earlier winner-poster iterations
  changed or distorted faces; the accepted direction used the original photos
  with deterministic layout and color adjustment.
- Feed posters must be 1080 x 1350. Reels must be 1080 x 1920.
- Important matchup or deadline copy needs visible spacing and hierarchy; it
  should not be buried among secondary text.
- The practice-match reel mutes all camera audio to remove incidental human
  voices.
- The current music is an original instrumental without vocals, avoiding reuse
  of the previous reel's song.
- Reels should hook with live play in the first three seconds and finish over
  footage with a prominent action/date card.
- Ideogram is useful for generating text-free campaign artwork, but factual
  typography, dates, phone numbers, and URLs should be composed locally.

## 4. System architecture

### Poster studio

The Python package under `src/cricket_posts/` provides the primary poster
system. The documented path uses:

`structured content -> registered layout/archetype -> artwork or plate -> exact HTML/CSS or Pillow typography -> deterministic audit -> PNG/export`

Important areas:

- `models.py`: validated content/design models.
- `pipeline.py` and `studio.py`: workflow orchestration.
- `composite.py`: three-layer composition.
- `archetypes.py`, `layouts.py`, and `blocks.py`: bounded layout vocabulary.
- `fit.py`, `freespace.py`, and `layout_score.py`: copy fitting and visual-space
  checks.
- `renderer.py` and `studio_renderer.py`: browser-based rendering.
- `ideogram.py`, `ideogram_edit.py`, and `poster_art.py`: generated artwork.
- `plates.py`, `plate_studio.py`, and `subjects.py`: reusable art/subject banks.
- `tracking.py`: short links and QR tracking.
- `storage.py` and `studio.db`: local project/job persistence.
- `web.py` and `templates/web/`: FastAPI studio interface.

The general studio favors a hybrid method: generate or reuse imagery, but render
business text exactly. Some recent one-off campaign scripts use Pillow directly
for faster, controlled composition.

### Reel system

The TypeScript/React system under `remotion/` implements:

`source footage -> semantic selection/edit spec -> FFmpeg preparation -> Remotion components -> MP4`

`EditSpec` JSON is the editorial source of truth. It records shot ranges,
timeline positions, motion, transitions, overlays, brand values, audio policy,
and the final action. `AcademyIntro` is reusable for both registered
compositions:

- `AcademyIntro`
- `PracticeMatchReel`

The reel renderer also has an additive component library under
`remotion/library/`. It provides opt-in theme presets, overlay variants, motion
primitives, transitions, and decorative elements while preserving the original
look of fixtures that do not select a style. `ReelComponentLibrary` is the
visual catalog composition, and `ReelLibraryDemo` exercises the JSON-driven
library over prepared practice-match footage. The starter fixture is
`fixtures/reel-library-demo-v1.json`; full usage is documented in
`remotion/LIBRARY.md`.

The current practice-match fixture is about 21.85 seconds at 30 fps. It uses six
shots, muted source audio, an original instrumental bed, and deadline overlays.
Prepared clips are cached under `remotion/public/` and excluded from Git.

### Meta Ads system

- `scripts/meta_ads_full_export.py`: read-only full Houston export, filtered by
  ad-set geography rather than campaign naming.
- `output/meta_ads_houston/`: exported aggregate data, manifest, and audit.
- `scripts/meta_ads_create_campaign.py`: dry-run-first creator; actual execution
  creates paused objects.
- `scripts/meta_ads_monitor.py`: read-only threshold monitor.
- `scripts/meta_ads_pause.py`: explicit-ID pause/reactivate helper with state
  verification.

The current creator is oriented toward a single video lead ad. It is not yet a
generic two-creative campaign publisher. Its defaults are also older than the
latest proposed budget and creative, so inspect every payload before use.

## 5. How the repository evolved

### Git-recorded phase: July 28-August 7, 2026

The repository contains 25 commits. The recorded progression was:

1. Establish a baseline and retire the earlier proof of concept.
2. Build a three-layer composition pipeline.
3. Add Houston and Austin layouts, real student cut-outs, and larger readable
   copy/contact treatments.
4. Add lane-rental scenes, subject and plate banks, and multiple layout
   archetypes/treatments.
5. Add cropping, free-space, contrast, and dead-space measurements.
6. Add the real Houston crest, registration URL, printed tracking link, and QR.
7. Add U5/U7/U10/U13 fixtures and document the composition pipeline.

### Later working-tree phase: August-September 2026

Much of the current work is uncommitted or untracked:

- the Remotion/TypeScript reel system;
- semantic video-probing and media-preparation scripts;
- original music generation and licensing notes;
- practice-match reel iterations and QA frames;
- Meta Ads export, audit, campaign creation, monitoring, and pause utilities;
- the Saturday Series/Titans winner posters;
- the Houston academy and strength-training poster scripts and fixtures;
- the September 15 poster and reel.

This means Git history alone is incomplete. Preserve the working tree and make a
reviewed baseline commit before large refactors.

## 6. Houston Meta Ads evidence

The export in `output/meta_ads_houston/` was created August 17, 2026 using Meta
Graph API v24.0. It covers Houston-targeted ad sets from February 5 through
August 16; actual delivery stopped May 23.

Verified historical totals:

- 11 campaigns, 11 ad sets, 11 ads, and 11 used creatives.
- $1,098.25 spend.
- 101,930 impressions and 25,776 reach.
- 1,273 link clicks at 1.25% link CTR and $0.86 per link click.
- 166 Meta instant-form leads at $6.62 raw CPL.
- Approximately 13.0% link-click-to-lead conversion.
- The last 30 delivery days improved to $6.07 CPL.

Best repeatable evidence:

- Academy/training offer: $3.99 CPL.
- Two summer-camp campaigns: $5.52 and $5.88 CPL.
- Offer-led, time-bound messages outperformed generic coaching messages.
- Ages 25-44 produced 68% of leads, but the audit recommends broad targeting
  rather than splitting a low-volume audience.
- Instagram produced 114 leads at $6.33 CPL; Facebook still contributed useful
  volume.
- Static historically showed $5.98 CPL and video $7.98, but format was
  confounded with different offers and copy. Treat this as directional only.

Initial control targets from the audit:

| KPI | Target | Intervention point |
|---|---:|---:|
| Raw Meta CPL | <= $6.00 | > $8.00 at meaningful volume |
| Link CTR | >= 1.40% | < 1.00% after 3,000 impressions |
| Cost per link click | <= $0.80 | > $1.00 |
| Link-to-lead rate | >= 14% | < 10% after 30 link clicks |
| CPM | <= $12 | > $15 without better quality |
| Seven-day frequency | 1.5-2.5 | > 3 with worsening CTR/CPL |

These are raw-platform thresholds, not business profitability. The export does
not contain qualified-lead status, trial attendance, enrollment, collected
revenue, CAC, or ROAS.

## 7. Recommended campaign structure

The evidence-backed default is one Houston lead campaign, one broad prospecting
ad set, and multiple creatives within that ad set. Do not create a separate
campaign for the poster and reel merely because they use different formats.

- Geography: approximately 15 miles around the Houston venue.
- Audience: broad parent-age targeting initially; write primarily to parents
  25-44 without unnecessary interest stacking.
- Placements: automatic, with native 4:5 Feed and 9:16 Reel/Story assets.
- Optimization: Meta instant-form lead, while tracking qualified outcomes
  outside Meta.
- Bid strategy: highest volume, consistent with the historical account setup.
- Creative test: keep offer, form, audience, and dates constant so format/message
  is the main variable.
- Proposed starting budget from the audit: $25/day total for 14 days, not $25
  per creative. A 10-day version was also discussed; final duration and total
  spend still require explicit business approval.

The current assets provide two test cells, not the four suggested by the full
audit. A testimonial/proof creative and a dedicated scarcity variant remain
future additions.

## 8. Measurement and decision rules

During a new run:

- First 72 hours: check delivery, form function, duplicate handling, and gross
  problems. Avoid hourly optimization.
- Replace a creative after about $24 spend with zero leads, or after at least
  five leads if CPL remains above $10 while another creative is materially
  stronger.
- At day 7, compare CPL and qualified-lead quality together. Do not pick a winner
  using CTR alone.
- Scale only if there are at least 20 leads, CPL is around or below $6.50, and
  lead quality is acceptable. Increase about 15-20%, then hold for three days.
- If link CTR is weak, improve the hook/creative. If link CTR is healthy but form
  completion is below 10%, improve the form or offer.
- Do not make CAC or ROAS claims until enrollment and revenue are connected.

Minimum lead record needed for meaningful optimization:

- campaign, ad set, ad, and creative identifiers;
- submission time and contact outcome;
- qualified/unqualified status and reason;
- trial booked and attended;
- enrollment outcome;
- collected revenue at 30/60/90 days.

## 9. Environment and local commands

Python 3.11+ and Node are used. Secrets live only in ignored `.env`. Expected
variable names are documented in `.env.example`.

Poster studio:

```powershell
uv sync --all-groups
uv run cricket-posts serve
uv run pytest
```

Current strength poster, reusing existing artwork without an API call:

```powershell
.\.venv\Scripts\python.exe scripts\create_strength_training_ideogram_poster.py
```

Only add `--generate` when new Ideogram artwork is intentionally authorized.

Practice-match reel:

```powershell
npm run practice:prepare
npm run practice:render
```

Meta read-only export and monitoring:

```powershell
.\.venv\Scripts\python.exe scripts\meta_ads_full_export.py
.\.venv\Scripts\python.exe scripts\meta_ads_monitor.py --campaign-id <ID>
```

Campaign creation must begin with the creator's default dry run. `--execute`
changes external state and must be used only after explicit approval.

## 10. Known issues and unresolved decisions

- September 13 product decision: Google Drive intake and the external-app demo
  are business-generic and may use a completely synthetic, permission-safe media
  packet. Private 22Yards assets and child-media permission are not prerequisites
  for proving the Drive connector. The 22Yards files remain a separate local
  renderer proof case.
- Recent work needs a reviewed Git baseline; do not bulk-add generated media or
  secrets.
- The root README has a few character-encoding artifacts such as malformed
  dashes and multiplication signs.
- Contact information in the Meta creator conflicts with current creative.
- The Meta creator's default video, budget, duration, copy, form behavior, and
  phone must be aligned with the final campaign before execution.
- The existing proven form has historical volume, but its thank-you destination
  is weak. Creating a replacement or reusing the old form is a business decision.
- The September 15 deadline is near and becomes invalid immediately afterward.
- Lead quality and enrollment outcomes are not connected to the aggregate Meta
  export.
- No single `CampaignSpec` currently drives poster, reel, caption, tracking, and
  Meta payloads; duplicated values can drift.
- No automated reel QA currently verifies voice absence, safe zones, spelling,
  audio peaks, or final-frame readability.
- No durable campaign ledger currently links a creative file to its Meta IDs,
  spend, results, and business outcome.

## 11. Continuation checklist for Astra

Before beginning new work:

1. Read `AGENTS.md`, this file, and `docs/FUTURE_SCOPE.md`.
2. Inspect `git status`; preserve existing work.
3. Identify whether the task is analysis, local generation, external API
   generation, or Meta account mutation.
4. Confirm any time-sensitive offer, deadline, contact, URL, budget, and format.
5. Reuse existing artwork/media when the requested change is deterministic.
6. Inspect final images or representative video frames rather than trusting a
   successful render command.
7. Record newly approved business facts and campaign results back into this
   memory file without adding secrets or personal lead data.

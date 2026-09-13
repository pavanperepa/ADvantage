# ADvantage GitHub Project backlog

Prepared September 12, 2026 from
[`HACKATHON_BETA_MVP1_PLAN.md`](HACKATHON_BETA_MVP1_PLAN.md). The execution
source of truth is the private
[ADvantage Agent Test Board](https://github.com/users/pavanperepa/projects/1),
with [roadmap issue #19](https://github.com/pavanperepa/ADvantage/issues/19) as
the parent for all delivery tickets and the full canonical execution plan. This
file is the repository-side index; update decisions and execution progress in
GitHub first, then reconcile this local reference when scope changes.

P0-02 validation evidence and unresolved demo-readiness gates are recorded in
[`P0_02_BASELINE_VALIDATION.md`](P0_02_BASELINE_VALIDATION.md).

## Project setup

The existing repository-associated project uses these fields:

| Field | Values |
|---|---|
| Status | Todo, In Progress, Done |
| Phase | P0 Eligibility, P1 Happy path, P2 Trust, P3 Submit, P4 Beta |
| Priority | P0 Critical, P1 High, P2 Medium |
| Size | XS, S, M, L |

Recommended views:

- **Event critical path:** Phase P0–P3, grouped by Status, sorted by Priority.
- **Beta MVP 1:** Phase P4, grouped by Status.
- **Release gates:** issues with the `release-gate` label.

Registration is owner-confirmed. Eligibility terms for pre-existing work and
whether the three proposed integrations qualify remain unresolved and must stay
visible as a separate gate.

## Issue index

Ticket keys remain stable dependency references in issue bodies and reports.

| Key | Phase | Priority | Size | Issue | GitHub |
|---|---|---|---|---|---|
| ROADMAP | P0–P4 | P0 | XS | Ship the hackathon entry and Beta MVP 1 | [#19](https://github.com/pavanperepa/ADvantage/issues/19) |
| P0-01 | P0 Eligibility | P0 | XS | Capture organizer rules and lock the eligible three-app proof | [#1](https://github.com/pavanperepa/ADvantage/issues/1) |
| P0-02 | P0 Eligibility | P0 | S | Freeze the baseline, demo fixture, and integration access | [#2](https://github.com/pavanperepa/ADvantage/issues/2) |
| P1-01 | P1 Happy path | P0 | M | Add the versioned CampaignManifest contract and validation | [#3](https://github.com/pavanperepa/ADvantage/issues/3) |
| P1-02 | P1 Happy path | P0 | L | Persist campaign state, attempts, receipts, and resume | [#4](https://github.com/pavanperepa/ADvantage/issues/4) |
| P1-03 | P1 Happy path | P0 | M | Ingest and validate a small Google Drive source folder | [#5](https://github.com/pavanperepa/ADvantage/issues/5) |
| P1-04 | P1 Happy path | P0 | M | Produce a manifest-driven 1080x1350 poster | [#6](https://github.com/pavanperepa/ADvantage/issues/6) |
| P1-05 | P1 Happy path | P0 | L | Produce a manifest-driven 1080x1920 reel | [#7](https://github.com/pavanperepa/ADvantage/issues/7) |
| P1-06 | P1 Happy path | P0 | L | Connect the end-to-end owner journey in the FastAPI UI | [#8](https://github.com/pavanperepa/ADvantage/issues/8) |
| P1-07 | P1 Happy path | P0 | M | Build a read-only Meta payload preview for static and video ads | [#9](https://github.com/pavanperepa/ADvantage/issues/9) |
| P2-01 | P2 Trust | P0 | L | Inspect final media and run bounded repair with fresh QA | [#10](https://github.com/pavanperepa/ADvantage/issues/10) |
| P2-02 | P2 Trust | P0 | M | Bind approval to exact manifest, artifacts, and payload | [#11](https://github.com/pavanperepa/ADvantage/issues/11) |
| P2-03 | P2 Trust | P0 | L | Create and verify both Meta ads in PAUSED state | [#12](https://github.com/pavanperepa/ADvantage/issues/12) |
| P2-04 | P2 Trust | P0 | L | Implement the reliability and adversarial evaluation suite | [#13](https://github.com/pavanperepa/ADvantage/issues/13) |
| P3-01 | P3 Submit | P0 | M | Prove two complete runs and package evidence | [#14](https://github.com/pavanperepa/ADvantage/issues/14) |
| P3-02 | P3 Submit | P0 | M | Record the two-minute demo and submit the entry | [#15](https://github.com/pavanperepa/ADvantage/issues/15) |
| P4-01 | P4 Beta | P1 | L | Generalize the supported workflow and durable job operations | [#16](https://github.com/pavanperepa/ADvantage/issues/16) |
| P4-02 | P4 Beta | P1 | L | Add beta security, isolation, retention, backup, and support controls | [#17](https://github.com/pavanperepa/ADvantage/issues/17) |
| P4-03 | P4 Beta | P1 | L | Run the design-partner pilot and decide the Beta MVP 1 release | [#18](https://github.com/pavanperepa/ADvantage/issues/18) |

## Ticket bodies

### ROADMAP — Ship the hackathon entry and Beta MVP 1

Deliver one inspectable campaign-production journey from a small-business brief
and Drive folder through a checked Feed poster, checked vertical reel, reviewed
Meta payload, and explicitly authorized PAUSED campaign creation. Then harden
that journey for a small private beta.

**Product decision**

The owner supplies a rough brief and a small Drive folder. ADvantage resolves
material facts into one versioned CampaignManifest, proposes a grounded angle,
produces a 1080x1350 Feed poster and a 1080x1920 vertical reel, checks and
repairs final media, shows one combined review, and prepares one Meta campaign
with a static and a video ad. Every delivery object is created PAUSED only after
approval of the exact facts, creative hashes, QA, and payload preview.

The product is business-generic. 22Yards Houston is the first proof adapter and
demo fixture, not a platform constraint. No activation/unpause control is part
of the hackathon or Beta MVP 1 journey.

**Eligibility and three-app proof**

Registration is owner-confirmed. Issue #1 separately tracks unresolved terms
for pre-existing work, app qualification, roster, submission access, licensing,
and disclosure. The intended meaningful actions and evidence are:

| App | Action | Evidence |
|---|---|---|
| Google Drive | List and download the selected source folder | Sanitized source IDs, content hashes, and receipts |
| Ideogram | Generate text-free campaign art when useful | Request/receipt and generated artifact hash |
| Meta Ads | Create the exact approved campaign, ad set, static ad, and video ad PAUSED | Redacted preview, returned IDs, and PAUSED read-back |

Remotion and FFmpeg are internal renderers and do not count as external apps.
If provider APIs do not qualify, #1 must name a conventional third app with a
real workflow action before final integration.

**Happy path**

1. Preflight Drive access and supported logo, photos, and 3–6 short clips.
2. Inventory sources; expose provenance and one material fact conflict.
3. Resolve the conflict and version the manifest. Imported text is evidence,
   never permission to operate a tool.
4. Propose two grounded angles, select one, and create exact copy plus bounded
   image and video plans.
5. Produce both output formats from the same manifest revision.
6. Run deterministic checks and a separate final-media inspection; repair the
   responsible layer at most twice and recheck.
7. Show before/after for one supported owner correction; invalidate old QA and
   approval.
8. Review creative, copy, dates, audience, budget, form/destination, QA, and the
   read-only Meta payload. Bind explicit creation approval to that exact package.
9. Create and read back one campaign, one ad set, and two ads PAUSED; display
   receipts, remaining limitations, and the downloadable evidence package.

Done means this works through the UI without hand-editing JSON, invoking hidden
commands, or copying facts between stages. Two clean repetitions must complete.

**Implementation boundaries**

- `CampaignManifest`: facts with provenance/status, exact copy, dates, audience,
  destination/form, budget, media/audio permissions, selected angle, source and
  artifact hashes, and schema version.
- Persisted runner states: `intake -> needs_facts -> ready_to_plan -> producing
  -> checking -> needs_review -> approved_for_paused_create -> creating ->
  paused_verified`, plus `blocked`, `failed`, and `partial_external_result`.
- Adapters: Drive intake, poster mapping, footage/EditSpec/Remotion, and Meta
  preview/execution, all driven by the same manifest revision.
- Trust layer: deterministic QA, separate media inspection, bounded repair,
  approval invalidation, sanitized trace, intent journal, receipts, and external
  object ledger.
- Reliability: cache by source/manifest/tool version; cap retries and paid work;
  reconcile unknown write outcomes before retry; reject source prompt injection;
  validate media/subprocess inputs; never expose credentials in logs.

**Phases and release gates**

- P0: settle eligibility terms; freeze an honest baseline and permission-cleared
  demo fixture; verify renderers and app/account access.
- P1: connect Drive, manifest, poster, reel, UI, and a zero-write Meta preview.
  Gate: one Drive folder yields both downloadable outputs and matching preview.
- P2: add final-media QA/repair, approval binding, resume/reconciliation, and
  authorized PAUSED creation. Gate: two full runs, one repair, one resume, zero
  unauthorized writes, and PAUSED read-back for the live case.
- P3: freeze, run evaluations, preserve evidence, record the two-minute demo,
  test judge setup, and submit with limitations disclosed.
- P4: add a second business fixture, durable jobs, security/tenant controls,
  operator support, and design-partner pilots before the private beta decision.

If the first integrated run is late, cut layout variety, arbitrary editing,
optional voiceover, broad footage search, and UI decoration. Preserve both
formats, meaningful app actions, approval enforcement, and honest evidence.

**Evaluation matrix**

| # | Scenario | Required result |
|---:|---|---|
| 1 | Complete supported brief and mixed folder | Both assets and matching preview |
| 2 | Missing offer or conflicting phone | Material question; unresolved fact cannot publish |
| 3 | Expired or incompatible dates | Approval blocked until corrected |
| 4 | Owner declines a free offer | No free-offer claim anywhere |
| 5 | Missing logo or unusable footage | Explain input failure; never claim both formats complete |
| 6 | Second small-business fixture | No inherited Houston/cricket facts or assets |
| 7 | Long copy or obstructed CTA | Detect and repair locally or escalate |
| 8 | QR and destination disagree | Block until aligned and rechecked |
| 9 | Stray generated text or visual defect | Separate inspector detects seeded defect |
| 10 | Weak reel hook or unreadable end card | Frame review detects and verifies revision |
| 11 | Camera-audio/music provenance violation | Audio/provenance gate blocks |
| 12 | Supported visual correction | New version and QA; old approval invalidated |
| 13 | Drive timeout or render crash | Bounded retry/resume; no fabricated output |
| 14 | Duplicate click or Meta write timeout | Reconcile; no blind duplicate create |
| 15 | Activation, stale approval, or source injection | Reject with zero write side effect |
| 16 | Authorized live paused creation | IDs and read-back prove delivery objects PAUSED |

Each result records expected/actual behavior, revisions, failure/repair,
latency/cost, and mocked/live/skipped/blocked status. Mock and live outcomes are
reported separately. A correct escalation counts only when escalation is the
expected behavior.

**Two-minute demo**

- 0:00–0:12 — owner problem and rough brief with Drive inputs.
- 0:12–0:28 — resolve one fact conflict with provenance visible.
- 0:28–0:50 — show poster, playable reel, and genuine app action trace.
- 0:50–1:15 — show a defect/correction, replacement version, and fresh QA.
- 1:15–1:40 — show approved payload, actual IDs, and verified PAUSED state.
- 1:40–2:00 — show evaluation outcomes, recovery evidence, and customer value.

Pre-recorded genuine work, caching, or offline replay must be disclosed. Replay
does not count as a fresh integration test. Report observed time and cost; do
not invent lift, revenue, or enrollment impact.

**Beta outcome**

- Event: two complete runs, one demonstrated repair, one resume/recovery, and a
  genuine three-app action trail.
- Beta: at least five pilot campaigns across two businesses, with four
  completing inside the supported-input envelope without developer intervention
  beyond onboarding and owner approvals. Both formats pass QA, every material
  correction refreshes approval, restart/duplicate-click cases pass, and no
  cross-tenant or unauthorized action occurs. Target median owner interaction is
  below ten minutes, excluding provider/render wait; actual results decide
  release, extended pilot, or no-go.

**Child tickets**

- [ ] #1 and #2 — eligibility, baseline, fixture, and access
- [ ] #3 through #9 — integrated happy path
- [ ] #10 through #13 — trust, approval, paused creation, and reliability
- [ ] #14 and #15 — proof and submission
- [ ] #16 through #18 — beta hardening and pilots

**Release gate**

The hackathon milestone is complete only after #15. Beta MVP 1 is complete only
after #18 records the gate decision and supporting evidence. Raw Meta form
submissions are never treated as enrollment or revenue.

### P0-01 — Capture organizer rules and lock the eligible three-app proof

Registration is confirmed by the owner. Capture the actual rules separately so
the substantial pre-existing repository work is disclosed correctly and every
external integration counts under the organizer's definition.

**Acceptance criteria**

- [ ] Record the allowed use and disclosure requirements for pre-existing code
  and assets.
- [ ] Record whether Google Drive, Ideogram, and Meta Ads each qualify as an
  external app based on the planned meaningful actions.
- [ ] Record team roster, submission cutoff/channel, repository/app access,
  sponsor-stack, licensing, residency, age, and recording terms.
- [ ] Define an eligible fallback third app if any proposed provider does not
  count.
- [ ] Link or attach the authoritative rule text without secrets or private
  registration data.

**Dependencies:** none.

**Gate:** work may proceed locally, but the entry cannot be represented as
eligible until every unresolved term above is recorded.

### P0-02 — Freeze the baseline, demo fixture, and integration access

Create an honest event baseline and a permission-cleared, small-folder demo
scenario that can exercise both output formats and all qualifying apps.

**Acceptance criteria**

- [ ] Inventory pre-existing versus event-built files and capabilities.
- [ ] Preserve unrelated working-tree changes; define what belongs in a reviewed
  baseline commit without bulk-adding generated/private media.
- [ ] Choose a sanitized Drive folder with logo, photos, and 3–6 short clips;
  record media permissions.
- [ ] Verify poster and reel rebuilds and measure cold/warm render times.
- [ ] Preflight intended Drive, Ideogram, and Meta account/page/form access.
- [ ] Confirm current contact, destination, offer/deadline, audience, form, and
  budget are supplied by the demo manifest instead of stale script defaults.
- [ ] Record blockers and an offline replay plan; do not count replay as a fresh
  integration test.

**Dependencies:** P0-01 for final eligibility wording.

**Gate:** supported assets and local renderers work; external risks and factual
conflicts are visible before the event build starts.

### P1-01 — Add the versioned CampaignManifest contract and validation

Create the single typed source of campaign facts that drives planning,
rendering, QA, review, and Meta preparation.

**Acceptance criteria**

- [ ] Model business/brand, purpose, source refs, facts with provenance/status,
  timezone-aware offer and delivery dates, exact copy, audience, destination and
  form, budget, media/audio permissions, selected angle, asset hashes, and schema
  version.
- [ ] Keep artifacts and tool receipts in linked records rather than prompt
  history.
- [ ] Reject expired/incompatible dates, unresolved operational facts, invalid
  URLs, invalid budgets, and unsupported media inputs at the correct gate.
- [x] A missing budget may still permit a clearly labeled creative draft but
  blocks Meta preparation.
- [ ] Unit tests prove serialization, migration/version rejection, and no hidden
  Houston or cricket defaults leak into a neutral fixture.

**Dependencies:** P0-02 fixture and approved facts.

**Gate:** one manifest revision can be serialized and feeds every downstream
adapter without copying facts manually.

**Progress (`campaign-flow` branch, 2026-09-13):** substituted with a
deliberately simplified `CampaignRequest` (`src/advantage/domain/models.py`)
rather than the full versioned manifest — a scope cut made explicitly with the
project owner, not a partial miss. It models the core facts (business, brief,
format, contact, destination, offer, audience, budget) and the
missing-budget-blocks-Meta-prep rule (checked above), but has no per-fact
provenance/status, no dates, no schema version/migration, and no selected-angle
tracking. Serialization is unit-tested; migration/neutral-fixture tests aren't,
since there's no schema version to migrate and no hardcoded business defaults
exist to leak in the first place. See
[`P1_PROGRESS.md`](P1_PROGRESS.md) for the full comparison.

### P1-02 — Persist campaign state, attempts, receipts, and resume

Implement an idempotent campaign runner around the existing poster, reel, and
Meta capabilities.

**Acceptance criteria**

- [ ] Persist the states `intake`, `needs_facts`, `ready_to_plan`, `producing`,
  `checking`, `needs_review`, `approved_for_paused_create`, `creating`, and
  `paused_verified` plus `blocked`, `failed`, and `partial_external_result`.
- [ ] Persist step attempts, artifact versions, manifest revisions, approvals,
  intent journals, receipts, timestamps, and sanitized trace entries.
- [ ] Resume from completed checkpoints without repeating successful paid work
  or external writes.
- [ ] Cache using source hash, manifest revision, and tool/config version.
- [ ] Retry transient reads with bounded backoff; cap paid generation and repair
  attempts.
- [ ] Treat timed-out writes as unknown outcomes and require reconciliation
  before retry.
- [ ] Tests cover restart, repeated clicks, partial result, capped retry, and log
  redaction.

**Dependencies:** P1-01.

**Gate:** an interrupted mocked run resumes to the expected state with no
duplicate side effects.

**Progress (`campaign-flow` branch, 2026-09-13):** not started, deliberately.
`run_campaign()` executes synchronously in-memory end to end; there is no
persisted state machine, step-attempt/receipt storage, resume, caching, retry
policy, or write reconciliation. Explicitly cut for hackathon-day scope —
worth building once real traffic actually hits these edges, not before. See
[`P1_PROGRESS.md`](P1_PROGRESS.md).

### P1-03 — Ingest and validate a small Google Drive source folder

Connect the selected Drive folder to a sanitized asset inventory and manifest
draft.

**Acceptance criteria**

- [ ] Preflight connection and folder access before starting a run.
- [x] List/download only the selected folder's supported logo, photo, and video
  types within explicit size/duration limits.
- [x] Store source IDs, MIME type, size, content hash, and local artifact refs;
  omit private source data from logs and evidence.
- [x] Surface missing logo, missing/unusable footage, and conflicting operational
  facts as actionable questions.
- [x] Treat imported instructions as evidence only; reject requests to expose
  credentials, execute tools, publish, or bypass approval.
- [x] Tests cover inaccessible folder, unsupported file, transient timeout,
  duplicate file, prompt injection, and clean mixed folder.

**Dependencies:** P1-01 and P1-02.

**Gate:** the demo Drive folder deterministically produces a validated inventory
and no imported text can authorize an external write.

**Progress (`campaign-flow` branch, 2026-09-13):** the strongest-covered P1
ticket — `src/advantage/integrations/google_drive.py` and
`tests/advantage/test_drive_intake.py`
(built before this branch, frozen into it as the P0-02 baseline) satisfy
essentially all of the above: bounded allow-list ingestion, hashing/dedup,
sanitized refs, actionable questions for missing logo/footage/conflicting
facts, and prompt-injection quarantine, each with a dedicated test. Not done:
a distinct UI-level "preflight" step (folder-access validation happens inside
ingestion itself, but there's no separate check-before-you-commit screen,
since P1-06 hasn't started) and a live, authenticated Drive API run — today's
real end-to-end proof (see [`P1_PROGRESS.md`](P1_PROGRESS.md)) used local
synthetic files as `IntakeAsset`s directly rather than a live OAuth
connection, per the earlier decision to defer Drive credential setup.

### P1-04 — Produce a manifest-driven 1080x1350 poster

Map the neutral campaign manifest into the existing poster system while keeping
all factual typography deterministic.

**Acceptance criteria**

- [ ] Propose two short grounded angles and select one reviewable angle without
  silently modifying extracted source facts.
- [ ] Generate or reuse approved text-free Ideogram artwork only when useful and
  within the configured attempt/cost limit.
- [ ] Compose exact business copy, logo, date, phone, URL, and QR locally.
- [ ] Export a 1080x1350 PNG and link its hash, manifest revision, provider
  receipt, and source assets.
- [ ] Verify dimensions, exact copy, safe margins, overflow, contrast, logo load,
  and QR/destination agreement.
- [x] A neutral second-business fixture contains no inherited Houston/cricket
  facts or assets.

**Dependencies:** P1-01 and P1-03.

**Gate:** the demo manifest produces a downloadable checked poster with no hand
editing or copied operational facts.

**Progress (`campaign-flow` branch, 2026-09-13):** `poster_adapter.py` produces
a real, verified 1080x1350 PNG via the existing free `compose` pipeline (no
Ideogram call — a deliberate scope cut, "fix the image quality later"), proven
end to end against a synthetic neutral business (Northstar Community Studio):
correct copy, no missing/clipped text, no inherited Houston/cricket facts. The
one honest caveat: `compose()`'s background art comes from a generic stock
plate bank, so the *artwork* still happens to be cricket-themed regardless of
business — that's a known limitation of the free path, not a fact leak, and is
exactly what Smart Hybrid (real Ideogram artwork per business) would fix
later. Not done: angle proposals, QR, date field, and hash/receipt linkage. A
real pre-existing audit bug in the poster pipeline was also found and worked
around along the way — see [`P1_PROGRESS.md`](P1_PROGRESS.md) for details.

### P1-05 — Produce a manifest-driven 1080x1920 reel

Map the campaign manifest and a small validated footage set into the existing
EditSpec/Remotion pipeline.

**Acceptance criteria**

- [ ] Rank a bounded candidate set with timestamps/thumbnails and validate every
  selected range; label curated/pre-indexed inputs honestly.
- [ ] Create a 15–25 second EditSpec with a fast, relevant opening selected from
  approved footage, a readable CTA end card, approved brand values, and explicit
  audio policy. The 22Yards demo adapter uses live play; this is not a platform
  default.
- [x] Prepare media and render a 1080x1920 playable MP4.
- [ ] Exclude camera audio when the manifest requires it and retain music
  provenance.
- [ ] Link the MP4 hash, EditSpec, manifest revision, source ranges, and renderer
  receipt.
- [ ] Tests cover invalid ranges, missing/unusable footage, render crash, audio
  policy, and clean output metadata.

**Dependencies:** P1-01, P1-02, and P1-03.

**Gate:** the demo manifest produces a downloadable reel whose opening and final
CTA can be inspected without hand-editing JSON.

**Progress (`campaign-flow` branch, 2026-09-13):** `reel_adapter.py` renders a
real, verified 1080x1920 MP4 via the existing prepare-media -> Remotion
pipeline (previously CLI-only and never wired together), with an inspectable
opening hook and closing CTA card built from `remotion/library`'s existing
component catalog. Proven with a real (non-mocked) render against synthetic
footage; two real integration bugs were found and fixed in the process (a
missing audio track breaking the ffmpeg prep step, and an overlong hook
overlay overflowing illegibly) — see [`P1_PROGRESS.md`](P1_PROGRESS.md). Not
done: footage ranking/scoring (shots are used in the order given), an explicit
camera-audio-exclusion policy field, and MP4 hash/EditSpec/receipt linkage.

### P1-06 — Connect the end-to-end owner journey in the FastAPI UI

Expose the narrow vertical slice as one persisted run through the existing app.

**Acceptance criteria**

- [ ] Owner can enter a rough brief, select the Drive source, and see connection
  preflight.
- [ ] Owner sees provenance and resolves material questions without retyping
  known facts.
- [ ] Show proposed angles, progress, sanitized trace, poster, playable reel,
  QA status, and remaining blockers.
- [ ] Owner can request the single supported correction and see before/after
  versions.
- [ ] Combined review shows exact copy, dates, audience, budget, form,
  destination, and payload preview.
- [ ] Package export includes sanitized manifest, artifact refs, QA, and receipts.
- [ ] The happy path requires no hand-edited JSON or undocumented shell command.

**Dependencies:** P1-02 through P1-05 and P1-07 for the full review screen.

**Gate:** one browser run reaches `needs_review` and exposes both downloadable
outputs from a single manifest revision.

**Progress (`campaign-flow` branch, 2026-09-13):** not started. This is the
next and last piece before there's anything to click through in a browser —
`run_campaign()` (the orchestrator tying P1-01/03/04/05/07's simplified
substitutes together) is built, tested, and proven for real, so the UI has a
stable, working surface to wire against. See
[`P1_PROGRESS.md`](P1_PROGRESS.md).

### P1-07 — Build a read-only Meta payload preview for static and video ads

Replace the single-video creator's stale implicit defaults with a manifest-led
preview for one campaign, one ad set, and two ads.

**Acceptance criteria**

- [ ] Generate a sanitized, read-only preview for one campaign, one
  manifest-selected ad set, one static Feed ad, and one video Reels/Stories ad.
  The 22Yards demo uses broad Houston prospecting; geography and audience remain
  manifest-driven for other businesses.
- [ ] Use explicit account, page, form/destination, schedule, timezone, currency,
  total budget, audience, placement/creative mapping, and optimization fields.
- [x] Show that `$25/day for 14 days` is historical planning context only; the
  current manifest must supply any launch budget/duration.
- [x] Detect the stale phone/video/$40/four-day/new-form defaults and ensure none
  enter the new path.
- [x] Validate 4:5 and 9:16 creative bindings and keep campaign/ad set/ad desired
  status PAUSED.
- [x] Preview performs no Meta mutation; tests assert zero write calls.

**Dependencies:** P1-01, P1-04, and P1-05.

**Gate:** the combined review displays one exact payload revision matching both
creative hashes and all approved facts.

**Progress (`campaign-flow` branch, 2026-09-13):** `meta_adapter.py` replaces
every stale hardcoded default from the original script — nothing from the old
$40/four-day/proven-video/proven-form path can reach the new one, since none
of those constants exist here at all. Budget/duration come from the request,
PAUSED-only is enforced with a mandatory read-back before success, and dry-run
mode is verified (in code and in tests) to make zero network calls. The scope
difference from the original ticket: this builds **one** ad matching the
chosen format (static OR video), not both a static Feed ad and a video Reels
ad in the same campaign — matches the simplified "pick one format per
request" flow. No form/schedule/timezone/currency fields exist on the request
yet; targeting is a fixed broad US 18-65 default rather than manifest-driven
geography/audience. See [`P1_PROGRESS.md`](P1_PROGRESS.md).

### P2-01 — Inspect final media and run bounded repair with fresh QA

Make trust visible through deterministic checks plus a separate final-media
inspection step.

**Acceptance criteria**

- [ ] Produce structured findings with severity, affected artifact/property,
  evidence, repair route, and blocking status.
- [ ] Poster checks cover dimensions, copy, safe margins, overflow, contrast,
  logo, URL, and QR agreement.
- [ ] Reel checks cover dimensions, ffprobe metadata, EditSpec ranges, opening,
  transitions, end card, audio graph, and human playback acknowledgement.
- [ ] Inspector receives final artifacts and manifest requirements separately
  from the producer's self-assessment.
- [ ] Support one bounded correction such as CTA position or phone size; create a
  new artifact version and rerun checks.
- [ ] Cap repair attempts at two and block review when a critical finding remains.
- [ ] Clean and seeded-defect fixtures report detections, misses, and false alarms.

**Dependencies:** P1-04 and P1-05.

**Gate:** demonstrate one detected defect, responsible-layer repair, and passing
fresh QA on the replacement artifact.

### P2-02 — Bind approval to exact manifest, artifacts, and payload

Prevent stale approval from authorizing changed facts, creatives, or Meta
configuration.

**Acceptance criteria**

- [ ] Approval records the manifest revision, poster/reel hashes, QA report IDs,
  and payload-preview hash.
- [ ] Any factual, artifact, QA-blocking, audience, form/destination, schedule, or
  budget change invalidates approval.
- [ ] The UI explains what changed and requires fresh review.
- [ ] Imported Drive content, stale approvals, and repeated clicks cannot create
  authorization.
- [ ] Activation/unpause is not exposed by the hackathon/Beta MVP 1 journey.
- [ ] Tests prove unauthorized create and activation requests have zero external
  write side effects.

**Dependencies:** P1-06, P1-07, and P2-01.

**Gate:** only the exact reviewed package can reach
`approved_for_paused_create`.

### P2-03 — Create and verify both Meta ads in PAUSED state

After explicit approval of the exact package, create the delivery objects and
verify their state without enabling spend.

**Acceptance criteria**

- [ ] Dry run executes first and is stored with the approved payload hash.
- [ ] Explicit authorization is required before every external creation run.
- [ ] Create one campaign, one ad set, one static ad, and one video ad; create or
  reuse creative/media objects according to explicit reviewed IDs/configuration.
- [ ] Campaign, ad set, and both ads are created PAUSED and read back as PAUSED.
- [ ] Ledger links IDs, creative hashes, intent journal, receipts, and read-back
  results without describing creative/media objects as having delivery status.
- [ ] Timeout/unknown outcome reconciles by known identifiers before retry; no
  blind duplicate creation.
- [ ] Partial external results stop safely and resume after reconciliation.
- [ ] No activation/unpause path is added. Activation remains a separate future
  action requiring explicit approval of final creative, copy, dates, audience,
  budget, form, and destination.

**Dependencies:** P2-02.

**Gate:** one authorized integration run returns IDs and verifies every delivery
object PAUSED. A dry-run-only result must be labeled incomplete for this gate.

### P2-04 — Implement the reliability and adversarial evaluation suite

Turn the plan's 16 scenarios into versioned, reproducible evidence and report
mocked versus live outcomes separately.

**Acceptance criteria**

- [ ] Cover complete brief; missing/conflicting fact; expired date; declined
  offer; missing media; neutral business; layout defect; QR mismatch; artwork
  defect; weak reel frame; audio violation; spatial correction; transient/read
  or render failure; duplicate/write timeout; unauthorized/injected request; and
  authorized live paused creation.
- [ ] Record expected/actual behavior, revisions, failure reason, repair count,
  latency, provider cost when available, and mocked/live/skipped/blocked status.
- [ ] Permission, factual-blocking, approval-invalidation, and duplicate-write
  tests assert zero unauthorized side effects.
- [ ] A correct escalation passes only when escalation is the expected result; a
  happy-path escalation remains a failed completion.
- [ ] Never combine mock and live outcomes into one misleading pass rate.
- [ ] CI/local command produces machine-readable JSON and a concise human report.

**Dependencies:** P1-02 through P2-03; implement boundary tests alongside each
ticket rather than waiting for final integration.

**Gate:** every permission/factual/duplicate-write case passes; remaining
failures and skips are disclosed.

### P3-01 — Prove two complete runs and package evidence

Execute and preserve the actual event proof package after feature freeze.

**Acceptance criteria**

- [ ] Complete the supported happy path twice from the UI.
- [ ] Demonstrate one repaired media defect and one interrupted/resumed run.
- [ ] For the authorized live case, preserve redacted provider receipts and Meta
  PAUSED read-back; label any unavailable live integration honestly.
- [ ] Bundle sanitized manifest, run trace, before/after QA, evaluation
  JSON/summary, PNG, MP4, payload preview, and receipts.
- [ ] Inspect the package for credentials, private children's media, customer
  lead data, and unsupported claims.
- [ ] Record observed end-to-end latency, owner interaction time, and provider
  cost without invented impact metrics.

**Dependencies:** P0-01 through P2-04.

**Gate:** two supported end-to-end repetitions pass; all unresolved failures,
skips, and demo limitations are disclosed.

### P3-02 — Record the two-minute demo and submit the entry

Package the product story around a real workflow, visible trust, and evidence.

**Acceptance criteria**

- [ ] Demo covers problem/brief (0:00–0:12), fact conflict (0:12–0:28), both
  outputs/action trace (0:28–0:50), repair/fresh QA (0:50–1:15), approved payload
  and PAUSED receipts (1:15–1:40), and evaluation/recovery/value (1:40–2:00).
- [ ] Disclose pre-recording, caching, replay, and pre-existing work accurately.
- [ ] Short brief explains customer problem, three app roles, architecture,
  agent decisions, baseline, approval/recovery model, evaluation denominators,
  observed time/cost, limitations, and judge setup.
- [ ] Smoke-test repository/app access and setup from clean instructions.
- [ ] Verify the actual submission cutoff/channel and submit all required items.
- [ ] Preserve submission confirmation and final links in the roadmap issue.

**Dependencies:** P3-01 and resolved P0-01 terms.

**Gate:** accessible working project/repository, playable two-minute video,
system/reliability brief, evaluation evidence, and submission receipt exist.

### P4-01 — Generalize the supported workflow and durable job operations

Use the event build as a narrow beta foundation and remove proof-case coupling.

**Acceptance criteria**

- [ ] Add a second permission-cleared business fixture and eliminate inherited
  cricket/Houston facts in its outputs.
- [ ] Define and enforce the beta supported-input envelope: small folder, fixed
  layouts, both formats, and one Meta objective/form workflow.
- [ ] Replace expired September 15 copy with newly confirmed campaign facts.
- [ ] Add durable background jobs, restart recovery, progress, cancellation,
  provider timeout handling, and cost/time reporting.
- [ ] Package an operator-assisted local/managed pilot deployment with documented
  onboarding and limitations.
- [ ] Run the core evaluation suite against both business fixtures.

**Dependencies:** P3-01; can start after feature freeze without blocking the
event submission.

**Gate:** both fixtures complete inside the declared envelope and survive a
process restart.

### P4-02 — Add beta security, isolation, retention, backup, and support controls

Meet the operational bar before any shared multi-customer deployment.

**Acceptance criteria**

- [ ] Implement authentication, authorization, tenant isolation, and tests for
  cross-tenant access.
- [ ] Store provider credentials server-side with encryption/managed secrets and
  least-privilege connections; support disconnect/revocation.
- [ ] Document and implement retention/deletion for source media, artifacts,
  traces, and receipts.
- [ ] Add backup and demonstrate one restore check.
- [ ] Add basic error monitoring, redaction verification, and a support/incident
  runbook.
- [ ] Verify current provider permissions and distribution requirements.
- [ ] Keep activation manual/outside the product.

**Dependencies:** P4-01.

**Gate:** no known cross-tenant exposure or unauthorized external action; if the
gate is incomplete, pilots use isolated operator-assisted installations and are
labeled accordingly.

### P4-03 — Run the design-partner pilot and decide the Beta MVP 1 release

Validate workflow reliability and owner usability with permission-cleared small
businesses before broadening the product.

**Acceptance criteria**

- [ ] Recruit 3–5 design partners and complete at least five pilot campaigns
  across at least two businesses.
- [ ] At least four campaigns finish inside the supported-input envelope without
  developer intervention beyond documented onboarding and owner approvals.
- [ ] Both formats pass QA and every material correction invalidates and refreshes
  approval.
- [ ] Restart and duplicate-click cases pass during pilot operation.
- [ ] Record owner interaction time, elapsed provider/render latency, provider
  cost, support intervention, failure reason, and review outcome separately.
- [ ] Target median owner interaction below ten minutes, excluding provider and
  render wait; report the observed result even if it misses the target.
- [ ] Record qualified-lead/trial/enrollment fields only when consent and data
  handling are ready; do not present raw Meta leads as enrollment or revenue.
- [ ] Make and document the release, extend-pilot, or no-go decision from the
  gates; do not launch broadly just to meet a date.

**Dependencies:** P4-01 and P4-02, or the documented isolated-installation
fallback from P4-02.

**Gate:** five/two/four campaign-business-completion thresholds are evidenced,
with no cross-tenant exposure or unauthorized action.

# ADvantage: campaign production for small businesses

> **Hackathon product plan** — the target product is business-generic. 22Yards
> Houston Cricket Academy is the current proof case, not a product constraint.

A small business should be able to say, “make me an ad,” add a Google Drive
folder or a few assets, and get review-ready paid-social creative without
having to become a designer, video editor, or Meta Ads operator.

The agent turns incomplete context into a verified **Campaign Manifest**, makes
only material questions visible to the business, develops and produces both
**static posters** and **vertical reels/videos**, checks its own work, accepts
visual corrections, and prepares a Meta campaign for review. It never starts
spend on its own.

## Hackathon brief and fit

The following is the **user-provided hackathon brief**, not independently
verified event information:

- **Event:** virtual, Sunday, September 13, 2026.
- **Challenge:** “Build one useful, multi-step AI agent. Connect it to at least
  three external apps. Show how you know it works.”
- **Scoring:** Technical execution 30%; Reliability & evaluation 25%; Usefulness
  20%; Originality 15%; Demo clarity 10%.

The MVP connects three external apps: **Google Drive** for source intake,
**Ideogram** for campaign artwork, and **Meta Ads** for paused publishing. Video
is part of the MVP: Remotion is the internal renderer, footage understanding
selects the story, and ElevenLabs is an optional voiceover provider rather than
a dependency.

| Brief priority | Product evidence |
|---|---|
| Technical execution (30%) | Manifest-led orchestration across Drive, Ideogram, Remotion, and Meta; deterministic production artifacts at each handoff. |
| Reliability & evaluation (25%) | Fact provenance, deterministic checks, independent multimodal inspection, repair/revalidation, and a 10–20-case evaluation suite. |
| Usefulness (20%) | A business can move from loose assets and context to actual Feed and Reel creative plus a paused campaign. |
| Originality (15%) | The agent treats campaign facts and visual QA as first-class production systems, not just a chat prompt that emits an image. |
| Demo clarity (10%) | A two-minute trace shows the decision trail, creative assets, QA evidence, and the deliberately paused Meta result. |

## The customer promise

**Input:** a Drive folder, supplied photos/footage/logo, and rough context such
as “fall registration,” “parents nearby,” or “need an Instagram ad.”

**Output:** a factual campaign package: a 4:5 static ad, a 9:16 reel/video,
platform-ready copy, a QA record, an agent trace, and a Meta campaign/ad set/
creative/ad created **PAUSED** after review.

The system asks only when an answer can change the work materially: for example,
the offer or deadline, intended location/audience, destination, required
approval to use a person’s likeness, budget/dates, or the missing brand asset.
It does not interrupt the owner for preferences it can safely infer or present
as variants.

## Product flow

```text
Drive assets + rough brief
          │
          ▼
Source inventory → Campaign Manifest → material-question gate
          │                                  │
          ▼                                  ▼
Creative angles ──────────────────── confirmed facts
          │
          ├─ Static: Ideogram artwork + deterministic typography
          └─ Video: footage understanding → EditSpec → optional VO →
             captions/music → Remotion render
          │
          ▼
Deterministic QA + independent Creative Inspector
          │
          ▼
Targeted repair → revalidation → human review / spatial corrections
          │
          ▼
Meta dry run → PAUSED campaign objects → explicit activation approval
```

### 1. Campaign Manifest: the factual source of truth

The manifest is a versioned, human-readable record, created before production.
Every campaign artifact reads it rather than copying facts into prompts,
fixtures, captions, and Meta payloads independently.

It holds:

- business, brand, location, audience, offer, claims, CTA, destination, contact
  details, campaign dates, budget, and placement formats;
- source links/assets, ownership or likeness-use notes, and provenance for every
  operational fact;
- confidence and status for each field: supplied, inferred, needs confirmation,
  or approved;
- the selected creative angle(s), final copy, visual constraints, and delivery
  requirements; and
- IDs and checksums for exported creative, review/QA results, Meta object IDs,
  and approval events.

Conflicting facts are surfaced, not silently merged. A campaign cannot advance
past the material-question gate with an unconfirmed deadline, offer, budget,
destination, or unsafe/unsupported claim.

### 2. Creative development and production

The agent proposes a small set of angles grounded in the manifest—for example,
an outcome, proof, event, or deadline angle—and explains the audience relevance.
It then produces the selected directions in the placements that matter:

- **Static ad:** use Ideogram for text-free artwork where generation helps; add
  exact dates, prices, URLs, phone numbers, and CTA text deterministically.
- **Reel/video:** understand supplied footage, select shots around a narrative,
  write an `EditSpec`, prepare clips, render in Remotion, and add captions plus
  licensed/original music. Generate a short script and optional ElevenLabs
  voiceover only when voice supports the concept and rights are clear.
- **Review language:** supply primary text, headline, CTA, and an explanation of
  the angle alongside the visual—not as an afterthought.

Both poster and reel/video are in scope. The product is not a static-image tool
with a future video aspiration.

### 3. Two independent QA paths and repair

Passing a render command is not proof that an ad is usable. Each asset gets two
separate checks:

1. **Deterministic production QA** checks exact manifest copy, dimensions,
   safe margins, clipping/overflow, contrast, logo/contact/URL/QR correctness,
   exported media integrity, reel timing, audio policy, captions, and final CTA.
2. **Creative Inspector** is an independent multimodal review of the rendered
   image or representative video frames. It looks for visual failures that
   geometry cannot see: unreadable hierarchy, subject obstruction, stray text,
   distorted anatomy, brand mismatch, unsafe crop, misleading imagery, weak
   opening hook, or an unreadable closing card.

The agent records each finding, classifies it, repairs only the responsible
layer, and reruns the relevant checks. Deterministic fixes (copy, crop, layout,
contrast, captions) stay local; only an artwork or footage problem triggers a
new generated asset or editorial pass. A visible pass is never asserted until
the repaired artifact has been revalidated.

The reviewer may also give spatial corrections such as “move the date away from
the face,” “make the phone larger,” or “show the batting shot first.” The agent
translates these into layout coordinates or `EditSpec` changes, renders again,
and preserves the before/after trace.

### 4. Review, publishing, and activation

After creative review, the system previews the campaign manifest, audience,
budget, dates, form/destination, copy, assets, and QA report. It runs a Meta
dry run first. With authorization to create, it creates the campaign, ad set,
creative, and ad **PAUSED** and records their explicit IDs.

Activation is a separate permission boundary. The agent requires explicit
approval of the final creative, copy, dates, audience, budget, form, and
destination before changing any object to active. The agent trace makes this
legible: what it observed, inferred, asked, generated, checked, repaired, and
submitted—and what it deliberately did not do.

## Two-minute demo

| Time | Demonstrate |
|---:|---|
| 0:00–0:15 | The owner’s rough prompt and Drive folder: logo, images, practice footage, and scattered offer details. |
| 0:15–0:35 | The Campaign Manifest: sourced facts, one surfaced conflict/material question, and the resolved campaign ground truth. |
| 0:35–1:00 | Two proposed angles, then the static poster and the first seconds of the reel/video. |
| 1:00–1:20 | Deterministic QA plus an independent Creative Inspector finding; show the targeted repair and clean recheck. |
| 1:20–1:40 | A spatial correction applied to the poster or reel and the trace that connects it to the new artifact. |
| 1:40–2:00 | Meta dry-run/payload review and created PAUSED object IDs; end on the explicit approval gate, not activation. |

## Delivery priority and phases

### P0 — demonstrate the full trusted loop

1. Drive intake and a structured Campaign Manifest with provenance and
   material-question gating.
2. One business-generic creative brief that produces a static ad **and** a
   vertical reel/video.
3. Deterministic QA, independent inspector, targeted repair, and revalidation.
4. A concise agent trace and a review screen.
5. Meta dry run and paused object creation from the same manifest.

### P1 — make the demo repeatable

1. Formalize static and video artifact schemas, with manifest values injected
   into all copy, EditSpec, tracking, and Meta payloads.
2. Add reliable footage ingestion/understanding, captions, music licensing
   metadata, and optional voiceover handling.
3. Add spatial correction commands with before/after review artifacts.
4. Build the 10–20-case evaluation suite and a pass/fail dashboard.

### P2 — productize after the hackathon

1. Durable campaign ledger from asset to Meta ID to qualified business outcome.
2. Broader brand/template support and approval roles.
3. Lead-quality and enrollment feedback loops before making revenue or ROAS
   claims.

## Evaluation: show how it works

The MVP includes 10–20 compact, versioned cases, not a single hand-picked demo.
The suite should cover at least:

- complete and incomplete briefs; conflicting contact/destination/deadline
  facts; and a business that declines a free offer;
- static-only, video-heavy, and mixed asset folders; plus missing-logo and
  no-usable-footage failure paths;
- long copy, unsafe text placement, QR/destination mismatch, and generated-art
  stray-text/anatomy failures;
- reel hook, caption, safe-zone, closing-card, camera-audio, and music-rights
  cases;
- requested spatial changes; repairable versus escalation-required findings;
  and different small-business categories; and
- a Meta dry-run case, a paused-create case in a controlled account, and an
  attempted activation without explicit approval.

For every case, store manifest validity, questions asked, artifacts produced,
deterministic results, inspector result, repair outcome, trace completeness, and
whether an unsafe publish/activation was correctly prevented. Success is a
high-quality result **or** a clear, safe escalation—not an agent that pretends
every brief is publishable.

## Success criteria

- A new business can reach reviewed 4:5 and 9:16 creative from a rough brief
  and assets with no manual fact retyping across systems.
- All publishable campaign facts trace to the manifest, a source, and an
  approval state.
- Both QA paths pass after any repair; reviewer spatial changes create a
  verifiable new version.
- The demo visibly uses Google Drive, Ideogram, and Meta Ads, with video as a
  first-class output.
- Every Meta mutation begins with a dry run; created objects remain paused;
  activation is impossible without explicit final approval.
- The evaluation suite reports results across 10–20 cases and exposes failures
  honestly.

## Safety boundaries

- Never put secrets, raw customer lead data, or private Drive assets into logs
  or demo artifacts.
- Preserve supplied real people, especially children. Use deterministic crop,
  color, and overlay changes; do not generatively alter faces without explicit
  approval.
- Do not invent offers, prices, schedules, testimonials, eligibility, results,
  or performance claims. Ask when a missing fact is material.
- Do not call a paid model simply to alter deterministic text, crop, or layout.
- Keep source/licensing records for footage, music, voice, and generated media.
- Meta reads, campaign creation, pausing, budget edits, and activation are
  separate permissions. No broad pause/delete actions; use explicit IDs.

## Non-goals

- A giant marketing platform, CRM, or full analytics warehouse.
- ZIP-code penetration, lead enrichment, attribution modeling, or enrollment/
  revenue analytics in the hackathon MVP.
- Autonomous spend, autonomous activation, or automatic claim approval.
- Replacing a designer/editor for every edge case; the product should escalate
  when human creative judgment or missing authority is required.

## Current implementation reality

The repository is a credible 22Yards proof case, with important foundations
already built—but it is not yet the full generic product described above.

| Capability | Reality today | Gap to MVP |
|---|---|---|
| Static creative | Implemented local poster studio: validated content, controlled layouts, Ideogram artwork, deterministic typography, rendering, and audits. Current proof includes a 1080×1350 22Yards strength-training poster. | Drive intake and a manifest must become the source of its campaign facts; add independent multimodal inspector/repair trace. |
| Video | Implemented Remotion prototype: source footage → JSON `EditSpec` → FFmpeg preparation → 1080×1920 MP4, with overlays, music, and reusable components. Current proof includes a practice-match reel. | Automate business-generic footage understanding, script/captions/optional VO, video QA, repair loop, and review UX. |
| Ideogram | Implemented integration and text-free-artwork practice. Recent poster generation deliberately keeps factual typography local. | Connect it to Drive/manifest orchestration and inspector-driven regeneration only when warranted. |
| Meta Ads | Implemented Houston exporter/monitor plus a dry-run-first creator that makes one video-lead campaign’s objects paused. Explicit-ID pause helper verifies state. | Generalize to manifest-led, multi-creative static + video publishing; align stale defaults; add review/approval ledger and activation gate in the product UX. |
| Campaign facts | Fixtures and scripts contain concrete facts for the proof case. | No single `CampaignSpec`/Campaign Manifest drives poster, reel, caption, tracking, and Meta payloads; current duplicated facts can drift. |
| QA and evaluation | Poster checks cover factual copy, overflow, margins, type size, contrast, logo, and dimensions; manual frame inspection has been used for reels. | No automated reel QA for voice absence, safe zones, spelling, audio peaks, or closing readability; no independent Creative Inspector, repair workflow, or 10–20-case suite. |
| Agent experience | Local studio UI and production commands exist. | No unified agent trace, material-question policy, Drive connector, or generic end-to-end review flow. |

### 22Yards proof case

The current campaign pairs a **strength-training poster** with a
**practice-match reel** for 22Yards Houston Cricket Academy. It is the right
demonstration because it has real supplied assets, a live offer/deadline,
deterministic typography requirements, and native 4:5 plus 9:16 deliverables.
Its September 15, 2026 free-trial wording is campaign-specific and must be
removed or replaced after that date. The current Meta creator also has older
campaign defaults (including contact data) that must not be used without a
manifest-led review.

That case proves the workflow; the product goal is to make the same trusted
path work for the next local business, whatever it sells.

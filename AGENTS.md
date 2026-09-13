# AI collaborator guide

This repository combines a cricket-poster studio, a Remotion reel editor, and
Houston Meta Ads analysis/automation. Before making changes, read these files in
order:

1. `PROJECT_MEMORY.md` for the business context, current deliverables, decisions,
   history, and known inconsistencies.
2. `docs/FUTURE_SCOPE.md` for the prioritized roadmap and launch checklist.
3. `README.md` for the poster engine and local application.
4. `remotion/README.md` for the video architecture.
5. `output/meta_ads_houston/HOUSTON_META_ADS_AUDIT.md` for the evidence behind
   Houston campaign targets.

## Current project state

- The maintained business in this workspace is 22Yards Houston Cricket Academy.
- The latest approved campaign concept pairs a strength-training poster with a
  practice-match reel. Both use a September 15, 2026 free-trial deadline.
- The poster is 1080 x 1350 (Instagram Feed 4:5); the reel is 1080 x 1920
  (Instagram Reels/Stories 9:16).
- The most recent creative and Meta Ads work is not yet represented in the
  existing Git commits. Do not assume `git log` describes the complete current
  system.
- The repository may have unrelated user changes. Preserve them and inspect
  `git status` before editing.

## Source-of-truth order

When two values conflict, use this order and surface the conflict instead of
silently guessing:

1. The user's latest explicit instruction.
2. The fixture or script used to produce the named current artifact.
3. `PROJECT_MEMORY.md`.
4. The main and Remotion READMEs.
5. Historical exports and older output files.

Dates, offers, prices, schedules, URLs, phone numbers, budgets, and Meta object
IDs are all changeable operational data. Verify them before publishing or
creating external objects.

## Non-negotiable safety rules

- Never print, commit, paste, or document secrets from `.env`.
- `.env.example` may describe variable names, but it must contain no live keys.
- Treat Meta reads, campaign creation, activation, budget changes, and pausing as
  different permission levels. A request to analyze data does not authorize a
  campaign mutation.
- `advantage.adapters.meta_ads.create_paused_campaign` defaults to a dry run and
  creates objects paused only when execution is explicitly supplied. The older
  `reference/main/scripts/meta_ads_create_campaign.py` is reference-only. Keep
  the active adapter's safety behavior.
- Never activate or unpause a campaign without the user's explicit approval of
  the final creative, copy, dates, audience, budget, form, and destination.
- Use explicit IDs for Meta mutations. Do not add a broad pause/delete mode.
- Preserve real children's faces. For supplied photographs, prefer cropping,
  brightness/color correction, and deterministic overlays. Do not generatively
  alter faces unless the user explicitly requests and approves that treatment.
- Ideogram should normally create text-free artwork. Add exact business copy
  deterministically so dates and contact information remain correct.
- Do not call a paid image/video API merely to change deterministic text, crop,
  brightness, or layout.

## Brand and campaign defaults

- Audience: U5-U13, beginner and intermediate players.
- Core outcomes: cricket skill development, physical fitness, strength, balance,
  movement, speed, and coordination.
- Match exposure is available when a child is developmentally ready; do not
  guarantee immediate match participation.
- Do not put a universal schedule or price in an ad. Age groups have different
  schedules, and pricing is handled after inquiry.
- Use direct parent-facing language. Avoid unsupported comparisons with other
  academies and avoid guarantees about performance, strength, or enrollment.
- Latest creative contact: `+1 (713) 498-2155`.
- Latest registration destination:
  `https://axon22yards.com/join?location=houston`.
- The current free-trial/deadline wording is campaign-specific, not an evergreen
  promise. Replace or remove it after September 15, 2026.

## Verification expectations

For posters, verify exact copy, logo, safe margins, contrast, QR destination,
contact details, and 1080 x 1350 dimensions. Inspect the final PNG visually.

For reels, inspect representative frames including the opening hook and final
CTA, verify 1080 x 1920 dimensions, play the exported MP4, and ensure there are
no incidental voices when the fixture says camera audio is muted.

For Meta work, perform a dry run first, inspect every payload, create only
paused objects, then confirm their state in Ads Manager. Report both raw lead
metrics and downstream lead quality; never treat form submissions as enrollment
or revenue.

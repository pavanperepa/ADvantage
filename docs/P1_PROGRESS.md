# P1 happy-path progress report

Written September 13, 2026 from the `campaign-flow` branch (branched off
`dev`). Covers tickets P1-01 through P1-07 in
[`GITHUB_PROJECT_BACKLOG.md`](GITHUB_PROJECT_BACKLOG.md) — the integrated
happy path. This is a status report, not a record of organizer-facing
completion; see that file's per-ticket "Progress" notes for the same
information inline with the original acceptance criteria.

## Why this says "simplified" more often than "done"

Partway into building these tickets as originally scoped, we deliberately cut
most of the versioned-manifest/provenance/dual-QA/approval-binding machinery
the original plan called for. That was an explicit decision, not a discovered
shortcut: the full apparatus exists to make trust *demonstrable to a judge*
(reliability & evaluation is 25% of the hackathon rubric), but most of it is
unnecessary weight for a first working version of the product, and some of it
— a persisted state machine, write reconciliation, a 16-scenario adversarial
suite — is genuinely premature before real usage exists to justify it.

So most tickets below are graded against their *original* acceptance criteria
honestly (mostly unchecked), while also describing the simplified substitute
that actually exists and works. Don't read a ticket as "failed" — read it as
"the narrow, load-bearing part is built and proven; the rest was a deliberate
cut."

## Status at a glance

| Ticket | Original scope | What exists now |
|---|---|---|
| P1-01 | Versioned, provenance-tracked CampaignManifest | Simplified `CampaignRequest` (no provenance/dates/schema version) — deliberate substitute |
| P1-02 | Persisted state machine, resume, reconciliation | Not started — deliberately deferred |
| P1-03 | Drive ingestion, validation, quarantine | Done (built in a parallel session, frozen into this branch's baseline) |
| P1-04 | Manifest-driven poster via Ideogram | Simplified: free `compose` pipeline instead of Ideogram, proven end to end |
| P1-05 | Manifest-driven reel via ranked footage | Simplified: straight-cut footage instead of ranked selection, proven end to end |
| P1-06 | FastAPI owner journey UI | Not started — the next piece of work |
| P1-07 | Manifest-led static + video Meta preview | Simplified: one ad per request (matching chosen format), proven safe |

Four of seven tickets (P1-03, P1-04, P1-05, P1-07) have a working, tested,
and — for P1-04/P1-05 — actually-run-for-real substitute behind them. P1-01 is
a real but much smaller contract than specified. P1-02 and P1-06 haven't
started.

## The real (non-mocked) happy-path proof

Unit tests for the reel and Meta adapters mock the expensive/external parts
(subprocess, Node, the Graph API) by design. Before starting UI work, we ran
the actual, unmocked pipeline end to end for both formats against the
synthetic "Northstar Community Studio" demo packet
(`output/drive_demo_source/`, from P0-02) via
`orchestrator.run_campaign()`:

- **Poster:** ~2.5s, real 1080x1350 PNG, verification passed with zero
  findings, correct Meta preview built (budget math, copy, CTA, destination
  all derived from the request).
- **Reel:** ~52s after fixes below, real 1080x1920 MP4 at 12.01s, verification
  passed, correct Meta preview for the video format.

Actually looking at the rendered output (not just automated pass/fail flags)
surfaced two real integration bugs no mocked test could have caught, both
fixed on this branch:

1. **Missing audio track broke ffmpeg prep.** The synthetic demo clips had no
   audio stream at all; `scripts/media/prepare_remotion_media.py`'s ffmpeg filter
   graph unconditionally references `[0:a]`, so it failed on any video-only
   input with "matches no streams." Real camera/phone footage always has an
   audio track (even if a policy later mutes it), so the fix was muxing a
   silent track into the synthetic clips at generation time
   (`scripts/demo/create_drive_demo_packet.py`), not touching the shared,
   already-tested filter graph other reels also depend on.
2. **The opening hook overlay overlapped and became unreadable.**
   `remotion/library`'s `HookTitle` component sizes its `line2` field at
   120px (82px past 20 characters) with no wrap/overflow protection — a punch
   line, not a sentence. `reel_adapter.py` was feeding it a 60-character offer
   sentence. Fixed by clipping to a real word boundary within 20 characters;
   the full offer still appears in full on the closing card, whose `headline`
   field does wrap cleanly at any length. Confirmed by re-rendering and
   comparing extracted frames before and after.

One more bug was found and documented but deliberately not fixed (out of
scope for an adapter to patch shared rendering code):

3. **A pre-existing false-positive in the poster's clipped-copy audit.** The
   default `info_variant="bar"` contact treatment assumes a banner always
   follows it (see `canvas.css`'s `--bar-drop`); with no banner (true of every
   `CampaignRequest`, which has no tagline field), one overflowing footer
   element made `pipeline.py`'s ancestor-chain audit report all 12 copy values
   as `CLIPPED`, not just the one that overflowed. Reproduced independently
   via the CLI (`--info bar` vs. `--info stack` against
   `fixtures/information.json`). Worked around in `poster_adapter.py` by using
   the already-supported `"stack"` treatment instead of the default.

One visual-only observation, not caught by any automated check and not acted
on: looking at the real composed poster, the body copy sits very tight
against the destination URL/phone line beneath it — not clipped, just
crowded. This is exactly the gap between "geometry checks pass" and "a human
looks at it" that the original plan's independent Creative Inspector step was
meant to cover, and that step is one of the ones we cut.

## What's next

P1-06 — the FastAPI UI wiring a request form, a combined review screen, and a
"create paused campaign" action to `orchestrator.run_campaign()` and
`meta_adapter.create_paused_campaign()` — is the last piece before there's
something to click through in a browser. The render and preview calls exist,
are tested, and have been proven against a real render for both formats. The
application/job and approval boundaries listed below still need to be built
before those calls are exposed through HTTP.

## Repository organization update

Later on September 13, the active flow moved from `src/cricket_posts/campaign/`
to the product package under `src/advantage/`. The deterministic poster engine
remains under `src/cricket_posts/` because it is still an active adapter
dependency. Superseded scripts, reel plans, and unreferenced Houston imagery now
live under `reference/main/`.

Versioned owner-UI request/response models are defined in
`src/advantage/api/contracts.py`; `docs/API_CONTRACTS.md` records the proposed
HTTP surface. These are contracts, not implemented routes. The Drive-to-job
mapper, persistent run service, asset-driven brand handling, stronger QA, and
approval-bound paused creation remain pre-UI application work.

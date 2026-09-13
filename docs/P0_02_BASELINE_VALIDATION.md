# P0-02 baseline validation

Validated: September 13, 2026 (America/Chicago)

GitHub: [issue #2](https://github.com/pavanperepa/ADvantage/issues/2)

Branch: `dev` only

## Result

The existing poster and reel foundations rebuild successfully from the selected
local 22Yards proof assets. The Python and TypeScript checks pass, the output
dimensions are correct, the configured Meta account, page, and historical lead
form are readable, and live Ideogram v4 generation is verified. A generic,
read-only Google Drive adapter and a synthetic demo packet now pass locally.
P0-02 remains in progress only until a live OAuth-authorized Drive list/download
preflight is recorded.

No Meta objects were created or changed. Two owner-authorized Ideogram TURBO
generations were made as a bounded live verification; neither replaced an
approved campaign asset. No credentials or customer-level lead data were printed
or added to this file.

## Branch and baseline

- The former local branch `issue-1-hackathon-eligibility` was renamed to `dev`.
- `dev` tracks `origin/dev`; it was created at commit
  `1ba6b70fe77a1b8a0f8ca84b2ebe22e418d2de95`.
- `main` and `origin/main` remain at the same baseline commit and were not
  changed.
- All P0-02 documentation, commits, and pushes must stay on `dev`.

This commit is the declared pre-P0-02 code baseline. It already contains the
poster studio, Remotion renderer, Meta tooling, and the 22Yards proof case. Git
history alone cannot prove which portions qualify as pre-event work, so the
submission must disclose the baseline commit rather than claiming the whole
repository was created during the event.

At validation start, the working tree also contained the following user work.
It was preserved and not bulk-added:

- Modified: `README.md`, `docs/FUTURE_SCOPE.md`.
- Untracked planning docs created for this project:
  `docs/GITHUB_PROJECT_BACKLOG.md` and
  `docs/HACKATHON_BETA_MVP1_PLAN.md`.
- Untracked legacy/reference fixtures:
  `reel-academy-intro-v1.json`, `reel-coaching-probe.json`,
  `reel-coaching-v2.json`, `reel-coaching-v3.json`, and
  `reel-practice-match-v1.json`, now under `reference/main/fixtures/`.
- Untracked legacy/reference scripts: `create_titans_instagram_poster.py`,
  `create_titans_winner_poster.py`, `render_reel_draft.py`, and
  `shotstack_academy_intro.py` under `reference/main/scripts/`.

The planning docs and this validation record form the intended documentation
commit. The legacy/reference files remain outside that commit pending a separate
review.

## Local 22Yards render-validation packet

The following bounded local packet remains the source for the 22Yards renderer
proof. It is no longer required for the external Drive demonstration.

| Role | Local source | Bytes | SHA-256 |
|---|---|---:|---|
| Logo | `assets/brand/22yards-houston.png` | 300,473 | `34271C49BF28060911E3490CD19ABB58927F451CA5494D576EE3C28827A889FA` |
| Clip 1 | `vids/practice-match1.mp4` | 1,541,076 | `A1B28843CDAFF7AC9BC5E853B887D03E55A2D62F06E36094E4C94ADEEE58ED16` |
| Clip 2 | `vids/practice-match2.mp4` | 616,120 | `81ED7ADD4302897EB294C490252F8B7294F1818C15B169CB0AB3597B234F87B2` |
| Clip 3 | `vids/practice-match3.mp4` | 1,521,429 | `9D42D7027B81B2CEB049934FB4545D1364B572C410113CB60A34DD01EC293E58` |
| Poster artwork | `output/posters/strength-training-ideogram-artwork.png` | 5,338,517 | `4A5B92A0757DD45FE6E6D8B900978E4489E2704BDDE073E89AD3C68C1AFE1B3C` |
| Music | `assets/music/houston-sports-pulse-instrumental.wav` | 2,925,756 | `E6D4AC530A17886493575B906B20F60C327481A2FB87249D0C8CA573EA927367` |
| Poster facts | `fixtures/strength-training-free-trial-sept13-houston.json` | 1,733 | `37B968A76ABABF38F4525CD60A8370AF1D61F07770F39FE353D2913A7070745C` |
| Reel plan | `fixtures/reel-practice-match-v2.json` | 5,267 | `C750A6356504D3DADE2F8F332586A5D6BD43E888B945B48BF91EE31CE122ADE8` |

The three clips contain identifiable children and must remain private. They may
not be placed in the Drive demo or judge package without explicit permission.

## Generic Drive demo packet

The owner confirmed that Drive intake should prove the general platform rather
than depend on 22Yards media. `scripts/demo/create_drive_demo_packet.py` now creates a
neutral packet under ignored `output/drive_demo_source/`: one deterministic logo,
one deterministic photo, three three-second vertical MP4s, and a complete
fictional campaign brief. The brief marks every asset as synthetic and approved
for tests, recordings, and judge review, and states that imported content cannot
authorize external writes.

The Drive adapter in `src/advantage/integrations/google_drive.py` supports explicit folder
URL/ID parsing, folder preflight, bounded direct-child listing and download,
MIME/size/duration limits, content hashes, sanitized source references, duplicate
detection, conflict questions, and prompt-injection quarantine. Its synthetic
test suite passes 13 cases. The generated packet is reproducible and ignored by
Git; upload it to a small Drive folder for the live external-app receipt.

## Validation evidence

| Check | Result |
|---|---|
| Python suite | Exit 0; 300 tests collected, 299 passed and 1 skipped. Existing deprecation warnings only. |
| TypeScript | `npm exec tsc -- --noEmit` passed. |
| Poster rebuild | Two deterministic local runs passed: 1.909 s and 1.832 s. |
| Poster artifact | 1080x1350 PNG, 1,035,431 bytes, SHA-256 `FCE54A30DAC1CE58FD338835EDD4BB5DA95E05EBAB919614B7A845865F884726`. |
| Poster visual review | Logo, headline, offer, date, phone, URL, QR, and safe margins are visible; no clipping found. |
| Reel preparation | Forced source rebuild passed in 20.077 s; cached run passed in 0.304 s. |
| Reel render | Two runs passed: 152.035 s and 106.072 s. |
| Reel artifact | H.264/AAC MP4, 1080x1920, 30 fps, 21.89 s, 33,179,875 bytes, SHA-256 `E0A366CF5F1CBFCC870C96EDAA79245FE2029B81CBB9BCC0EB0D14EB95788882`. |
| Reel visual review | Opening action/hook and closing CTA frame are readable at representative timestamps. |
| Reel audio | Final file has one AAC stereo stream at 48 kHz; mean -28.8 dB and max -11.1 dB. Every shot has `audio: 0.0`; the composition adds the declared original music bed. Human full-playback confirmation remains required before submission. |

The validated rebuild output is
`output/practice-match-reel/22yards-practice-match-reel-sept-15.mp4`.
The previously approved campaign deliverable remains the separately named `v4`
artifact recorded in `PROJECT_MEMORY.md`; this baseline rebuild does not replace
that approval.

## Integration preflight

| Integration | Status | Evidence / limitation |
|---|---|---|
| Google Drive | Partial | Generic read-only Drive v3 adapter, localhost OAuth bootstrap, automatic access-token refresh, CLI, neutral demo packet, and 20 focused Drive/OAuth tests are implemented. User consent and the exact dummy folder URL/ID are still required to record the external list/download receipt. |
| Ideogram | Passed live | The configured key completed two bounded v4 TURBO generations on September 13, 2026. The first output was correctly rejected for invented text/logo; the second was visually inspected and accepted as text-free integration evidence. |
| Meta Ads | Passed read-only | Configured account is accessible and active (`account_status=1`), USD/CST6CDT; the configured page and historical lead form are readable, and the form reports ACTIVE. No write endpoint was called. |

### Live Ideogram evidence

The live check wrote only new evidence files under the ignored
`output/integration_preflight/` directory.

| Attempt | Result | Evidence |
|---|---|---|
| 1 | Rejected by visual QA: invented `Houston Academy` crest and gibberish text despite the no-text/no-logo instruction. | `ideogram-p0-02-live-20260913.png`; 1792x2240 PNG; 5,198,260 bytes; seed `845263327`; SHA-256 `4F92FBB4D4A0E4FC3860FA4370700B4948792E97187FC2D1623213C7DDBC701E` |
| 2 | Accepted as integration evidence: text-free and logo-free generic cricket strength-training scene with usable calm regions for deterministic copy. It is not an approved replacement for the current campaign artwork. | `ideogram-p0-02-live-retry-20260913.png`; 1792x2240 PNG; 4,960,205 bytes; SHA-256 `14B97CE7407BD46F3BCDE9101B132CD66F58575E88F2E60ADC39C3FFEED1FED7` |

This proves live authentication and generation while also preserving the
required independent visual rejection path. The API response did not provide a
non-empty request ID, so the artifact hash, dimensions, file size, date, prompt
path, and first-attempt seed are the retained non-secret receipt fields.

### Drive live proof still needed

Upload the generated neutral files from `output/drive_demo_source/` to any small
Google Drive folder. Ownership and business identity do not matter. Configure
the ignored local OAuth client values, register
`http://localhost:8765/oauth2/callback`, and run
`scripts/intake/google_drive_authorize.py` to complete read-only consent. Then
run `scripts/intake/google_drive_intake.py` with the exact folder URL/ID, retain
the sanitized `inventory.json` receipt, and verify its downloaded hashes against
the generated packet. An email address and folder name alone cannot identify or
authorize the folder.

## Operational fact check

The current poster/reel fixtures use:

- Contact: `+1 (713) 498-2155`.
- Destination: `https://axon22yards.com/join?location=houston` (display forms
  omit the scheme where appropriate).
- Offer: free trial with September 15, 2026 deadline.
- Audience: U5-U13; beginner/intermediate parent-facing campaign.

The legacy Meta creator is unsafe as the new campaign source because it still
hardcodes `+1 (713) 570-9054`, an older video, a $40 lifetime budget, four days,
and new-form behavior. No single manifest currently supplies audience, budget,
schedule, form/destination, poster, reel, and Meta payload. P1-01 and P1-07 must
remove these implicit defaults before any campaign creation.

Because today is September 13, the current offer has only two days remaining.
The owner must explicitly confirm the exact campaign start/end times, timezone,
total budget, form choice, and continued validity of the offer before a Meta
payload can be approved. Historical `$25/day for 14 days` guidance is not an
approved budget for this run.

## Offline replay and open gates

For the event demo, preserve a screen recording and the checked local PNG/MP4,
manifest/fixture hashes, QA frames, and a redacted Meta read receipt. Label this
as replay evidence if an external provider is unavailable; it does not count as
a fresh Drive, Ideogram, or Meta action.

P0-02 stays **In Progress** until the one remaining item is resolved:

1. Upload the synthetic packet to a Drive folder and record a successful live
   read-only list/download preflight plus sanitized source references and hashes.

After those confirmations, update issue #2, rerun only the affected preflight,
and move the ticket to Done. Do not repeat the full 300-test suite unless code
changes invalidate this baseline.

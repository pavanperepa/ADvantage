# P0-02 baseline validation

Validated: September 13, 2026 (America/Chicago)

GitHub: [issue #2](https://github.com/pavanperepa/ADvantage/issues/2)

Branch: `dev` only

## Result

The existing poster and reel foundations rebuild successfully from the selected
local 22Yards proof assets. The Python and TypeScript checks pass, the output
dimensions are correct, and the configured Meta account, page, and historical
lead form are readable. P0-02 remains in progress until the demo Drive source,
media-use permission, live Ideogram access, and final operational campaign facts
are confirmed.

No Meta objects were created or changed. No paid image generation was called.
No credentials or customer-level lead data were printed or added to this file.

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
  `reel-practice-match-v1.json` under `fixtures/`.
- Untracked legacy/reference scripts: `create_titans_instagram_poster.py`,
  `create_titans_winner_poster.py`, `render_reel_draft.py`, and
  `shotstack_academy_intro.py` under `scripts/`.

The planning docs and this validation record form the intended documentation
commit. The legacy/reference files remain outside that commit pending a separate
review.

## Selected demo asset packet

Use the following bounded local packet as the source for the 22Yards demo. A
future Drive folder should contain equivalent copies; Drive IDs and download
receipts do not exist yet.

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

The three clips contain identifiable children and must remain private. Before
the demo folder is treated as permission-cleared, the owner must explicitly
confirm that these exact assets may be used in the hackathon recording and
shared with judges. Store that approval in issue #2 without uploading private
media to the repository.

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
| Google Drive | Blocked | No Drive connector, credential variables, folder ID, or Drive adapter exists in the current runtime. P1-03 owns implementation. |
| Ideogram | Partial | `IDEOGRAM_API_KEY` is configured and the provider code is present. A live authentication call would require a generation request, so no paid call was made just for preflight. Existing artwork supports offline replay only. |
| Meta Ads | Passed read-only | Configured account is accessible and active (`account_status=1`), USD/CST6CDT; the configured page and historical lead form are readable, and the form reports ACTIVE. No write endpoint was called. |

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

P0-02 stays **In Progress** until all four items are resolved:

1. Create/select the sanitized Drive folder and record a successful read
   preflight plus asset hashes.
2. Confirm permission to use the exact child footage/artwork in the hackathon
   recording and judge package.
3. Verify Ideogram authentication during an authorized useful generation, or
   record an organizer-accepted alternative app path.
4. Confirm the final offer/deadline, schedule/timezone, audience, total budget,
   form, destination, and contact details for the demo campaign.

After those confirmations, update issue #2, rerun only the affected preflight,
and move the ticket to Done. Do not repeat the full 300-test suite unless code
changes invalidate this baseline.

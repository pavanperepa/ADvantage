# Earlier main-branch reference

This directory contains historical material that is useful for comparison but
is not part of the production import graph.

## Scripts

- `shotstack_academy_intro.py`: superseded external video renderer.
- `render_reel_draft.py`: superseded hand-built FFmpeg reel renderer.
- `twelvelabs_reel_probe.py`: footage-understanding prototype; useful when
  implementing ranked shot selection.
- `meta_ads_create_campaign.py`: stale Houston single-video creator retained as
  payload reference. Do not execute it for a new campaign.
- `create_titans_instagram_poster.py` and
  `create_titans_winner_poster.py`: campaign-specific one-off poster scripts.

Scripts assume they are invoked from the repository root. Paths that locate the
repository use `Path(__file__).resolve().parents[3]` after this move.

## Fixtures

The JSON files here are superseded reel plans. Active EditSpecs remain in the
root `fixtures/` directory because registered Remotion compositions or current
proof cases still consume them.

## Media

`media/` contains unreferenced Houston source screenshots/images that used to
sit at the repository root. They are retained for visual research only and are
never selected automatically.

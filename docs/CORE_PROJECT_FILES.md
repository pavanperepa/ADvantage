# ADvantage core project files

Status: reorganized on `campaign-flow`, September 13, 2026.

This file is the short keep/remove boundary. See `ARCHITECTURE.md` for dependency
rules and `API_CONTRACTS.md` for the owner-UI contract.

## Active product

- `src/advantage/api/`: strict, versioned HTTP request/response models.
- `src/advantage/domain/`: internal campaign and artifact models.
- `src/advantage/application/`: orchestration and verification use cases.
- `src/advantage/adapters/`: poster, reel, and paused Meta adapters.
- `src/advantage/integrations/`: read-only Google Drive intake.
- `tests/advantage/test_api_contracts.py` and the campaign/adapter/integration tests.

New application code imports `advantage`. Compatibility modules under
`src/cricket_posts/campaign/` and `src/cricket_posts/drive_intake.py` are
temporary migration shims, not the preferred API.

## Reusable engines required by the product

- `src/cricket_posts/`: deterministic poster engine. The application poster
  adapter still imports its archetypes, models, pipeline, and renderer.
- `templates/studio/`, accepted `assets/plates/`, `assets/fonts/`, and poster
  tests: runtime dependencies of that engine.
- `remotion/`: EditSpec-driven reel renderer and component library.
- `scripts/media/prepare_remotion_media.py`: FFmpeg preparation called by the
  reel adapter.
- Root Python/Node lockfiles and configuration.

These are not historical reference files even when their names are cricket-
specific. Moving them to `reference/` before replacing the active imports would
break the campaign flow.

## Maintained operations

- `scripts/demo/create_drive_demo_packet.py`: synthetic, permission-safe demo
  packet.
- `scripts/intake/google_drive_intake.py`: bounded Drive intake CLI.
- `scripts/media/generate_sports_instrumental.py`: current instrumental source.
- `scripts/meta/meta_ads_full_export.py`: read-only aggregate export.
- `scripts/meta/meta_ads_monitor.py`: read-only campaign monitor.
- `scripts/meta/meta_ads_pause.py`: explicit-ID pause/reactivate utility.
- `scripts/campaigns/22yards/`: current proof-case poster scripts, isolated from
  generic product defaults.

## Active fixtures

Root `fixtures/` contains inputs still used by poster tests, current proof cases,
or registered Remotion compositions. A fixture is an example/editorial input,
not a database and not a source for implicit campaign defaults.

Current campaign-specific sources remain:

- `fixtures/strength-training-free-trial-sept13-houston.json`
- `fixtures/reel-practice-match-v2.json`
- `fixtures/reel-practice-match-library-v1.json`
- `fixtures/reel-library-demo-v1.json`
- `fixtures/reel-academy-remotion-v1.json`

The stale `sept13` filename and time-sensitive September 15 offer remain known
cleanup/operational issues.

## Reference only

`reference/main/` contains superseded renderer experiments, the stale single-
video Meta creator, one-off Titans scripts, older reel plans, and unreferenced
Houston image-bank material. Production code must not import from this tree.

The reference index explains why each file remains and how it may inform new
implementation without becoming an implicit runtime dependency.

## Generated/local state

The following are not source code:

- `output/`, except for named deliverables/audit evidence during handoff;
- `remotion/public/` and `*.freespace.json`;
- `.venv/`, `node_modules/`, uv/pytest/mypy caches, and `__pycache__/`;
- `studio.db`;
- ignored `real-photo/` and `vids/` source media.

Never use a broad clean/delete command to organize these. Preserve named current
deliverables and sensitive supplied media according to `AGENTS.md`.

## Known pre-UI gaps

- Drive receipts are not yet mapped into persisted campaign jobs.
- The poster adapter ignores selected photos and uses a cricket plate.
- Reel preparation still copies a fixed 22Yards logo.
- Verification and paused-create approval binding are not yet enforced by an
  application service.
- No persistent/idempotent run repository or HTTP routes exist yet.

Those are product tasks, not reasons to mix historical files back into active
directories.

# ADvantage repository architecture

This document is the source of truth for where new work belongs. The repository
has one product application, two reusable creative engines, operational scripts,
and an explicit historical reference area.

## Runtime dependency direction

```text
owner UI / HTTP routes (next)
            |
            v
src/advantage/api          public, versioned transport contracts
            |
            v
src/advantage/application  campaign use cases and verification
            |
            +-----------------------+
            v                       v
src/advantage/adapters                  src/advantage/integrations
   | poster   | reel   | meta                         | drive
   v          v        v                              v
src/cricket_posts   remotion/   Meta Graph API     Google Drive
```

Dependencies point downward only. The reusable engines do not import the
ADvantage application or API. Nothing under `reference/` is imported by the
production application.

## Directory ownership

| Path | Classification | What belongs here |
|---|---|---|
| `src/advantage/api/` | Active product | Versioned request/response models used by the future UI and HTTP routes. |
| `src/advantage/domain/` | Active product | Internal campaign, artifact, verification, and Meta-preview models. |
| `src/advantage/application/` | Active product | Use-case orchestration and publish gates. |
| `src/advantage/adapters/` | Active product | Translation to poster, reel, and Meta implementations. |
| `src/advantage/integrations/` | Active product | External source/account clients such as Google Drive. |
| `src/cricket_posts/` | Reusable engine | Existing deterministic poster engine. It remains a runtime dependency until a neutral replacement exists. |
| `remotion/` | Reusable engine | EditSpec-driven vertical-video renderer and component library. |
| `scripts/` | Operations | Maintained commands grouped by `demo`, `intake`, `media`, `meta`, and campaign-specific proof cases. |
| `fixtures/` | Active examples | Inputs still used by tests, registered Remotion compositions, or maintained proof cases. |
| `reference/main/` | Reference only | Superseded scripts, fixture history, and unreferenced source imagery retained from the earlier repository. |
| `output/` | Generated/local evidence | Ignored artifacts, receipts, renders, and current review evidence. It is not application source. |
| `tests/advantage/` | Active product tests | API, domain, application, adapter, and integration coverage. |
| `tests/poster_engine/` | Engine tests | Reusable poster-engine behavior and its legacy engine UI. |

`src/cricket_posts/campaign/` and `src/cricket_posts/drive_intake.py` contain
temporary compatibility imports only. New code must import `advantage`.

## Needed now

- `src/advantage/` and its tests: the product contract and owner journey.
- `src/cricket_posts/`, `templates/studio/`, accepted plates/fonts, and their
  tests: the poster adapter still calls this engine.
- `remotion/`, `scripts/media/prepare_remotion_media.py`, Node metadata, and the
  active EditSpecs: the reel adapter calls this engine.
- `scripts/intake/`, `scripts/meta/`, and the API/provider configuration names
  in `.env.example`.
- Current 22Yards proof scripts under `scripts/campaigns/22yards/`, clearly
  separated from product defaults.

## Reference only

The files indexed by `reference/main/README.md` are retained for comparison or
selective reuse. Moving a useful idea back into production means implementing it
behind an active adapter with tests; production code must not import a file from
`reference/` directly.

## Not source of truth

Local caches (`.venv`, `node_modules`, `remotion/public`, pytest/mypy/uv caches),
`studio.db`, and most of `output/` are rebuildable. Current deliverables and QA
proofs can still be operationally important, but code must not discover product
defaults by scanning generated output.

## Next structural work

1. Implement API routes and a persistent run repository against the contracts
   in `src/advantage/api/contracts.py`.
2. Add a Drive-receipt-to-domain mapper that resolves safe `source_ref` values
   server-side; never accept filesystem paths from the client.
3. Replace the poster adapter's cricket plate and the reel preparer's fixed
   22Yards logo with request-selected assets.
4. Move the old poster-only FastAPI pages behind an explicit engine/demo entry
   point once the new owner UI exists.
5. Remove compatibility shims only after all downstream imports use
   `advantage`.

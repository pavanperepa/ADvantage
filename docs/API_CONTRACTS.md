# ADvantage API contracts

Contract version: `1.0`

The executable Pydantic models live in `src/advantage/api/contracts.py`. This
document fixes the HTTP vocabulary before UI implementation; routes are not
implemented yet and must not be presented as live endpoints.

Export the machine-readable JSON Schema bundle with:

```powershell
uv run python scripts/api/export_contracts.py
```

The generated `output/api-contracts-v1.json` is ignored build output, so clients
should generate it from the tagged source revision rather than edit it manually.

## Proposed HTTP surface

| Method and path | Request | Response | Side effect |
|---|---|---|---|
| `POST /api/v1/drive-intakes` | `DriveIntakeRequest` | `DriveIntakeView` | Read-only Drive list/download into an isolated server run. |
| `GET /api/v1/drive-intakes/{intake_id}` | none | `DriveIntakeView` | None. |
| `POST /api/v1/campaigns` | `CampaignDraftRequest` | `CampaignJobAccepted` | Creates a local draft/job only. |
| `GET /api/v1/campaigns/{run_id}` | none | `CampaignReviewView` | None. |
| `POST /api/v1/campaigns/{run_id}/renders` | none | `CampaignJobAccepted` | Starts local rendering; never writes to Meta. |
| `POST /api/v1/campaigns/{run_id}/meta/paused` | `PausedCampaignCreateRequest` | `PausedCampaignView` | Creates exact reviewed objects in PAUSED state only. |

## Contract guarantees

- Unknown fields are rejected and every body carries `schema_version="1.0"`.
- Client asset selections contain only sanitized source references, kind, and
  content hash. Raw provider IDs, source filenames, access tokens, and local
  filesystem paths are excluded.
- A reel requires at least one selected video.
- Offers require a timezone-aware expiry. Campaign schedules are timezone-aware,
  forward-moving ranges with an IANA timezone.
- Budget means lifetime total and currently supports USD explicitly.
- `.test` destinations are rejected at the HTTP boundary so the synthetic demo
  link cannot reach a publish flow.
- Camera audio defaults to `mute`; supplied-media permission is explicit.
- A paused-create request binds the exact manifest, artifact, and payload hashes
  reviewed by the owner and requires the literal confirmation
  `CREATE_PAUSED`.
- A successful paused result includes campaign, ad-set, creative, and ad IDs.

## Required implementation gates

The route layer must resolve selected asset references from a server-held intake
receipt, create a unique run directory, persist every state transition and Meta
ID, and reject stale approval hashes. A failed or incomplete verification must
never reach the paused-create adapter. Activation is intentionally outside this
contract.

The old poster-studio routes in `src/cricket_posts/web.py` are a separate engine
UI and are not this API.

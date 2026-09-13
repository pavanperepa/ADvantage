# ADvantage: hackathon delivery and beta MVP 1

Planning date: September 12, 2026. This is a proposed execution plan, not a record of shipped features or authorization to call paid providers or mutate Meta. Default staffing assumption: one builder; beta target: a private pilot within two weeks after the event, subject to the gates below.

Execution is tracked in the private
[ADvantage GitHub Project](https://github.com/users/pavanperepa/projects/1).
The repository-side ticket index, dependencies, and acceptance criteria are in
[`GITHUB_PROJECT_BACKLOG.md`](GITHUB_PROJECT_BACKLOG.md); the parent roadmap is
[issue #19](https://github.com/pavanperepa/ADvantage/issues/19).

## 1. Product decision

Build one dependable campaign-production journey: a small-business owner supplies a brief and a Drive folder; ADvantage resolves material facts, makes a Feed poster and a vertical reel, checks and repairs them, and prepares a reviewed Meta campaign with delivery disabled.

Our competitive advantage should be **a campaign you can inspect and trust**: the same approved facts reach every output, visual corrections produce traceable versions, and external actions have evidence. Beautiful creative is necessary; the full cross-app workflow and demonstrated recovery make the entry more compelling.

Keep the business-generic direction in `FUTURE_SCOPE.md`. Use 22Yards as the first supported adapter and proof case. Prove the neutral contract with a second, permission-cleared small-business fixture before claiming broader support. Neither hackathon success nor commercial results are guaranteed.

## 2. Event requirements and eligibility gate

The [official event page](https://multiappagenthackathon.com/) was checked September 12, 2026. It lists a virtual September 13 event, a useful multi-step agent connected to at least three external apps, teams of 1–4, and submission of a working project/repository, a two-minute demo, and a short system/reliability brief. Scoring is technical execution 30%, reliability/evaluation 25%, usefulness 20%, originality 15%, and demo clarity 10%.

The linked [registration form](https://docs.google.com/forms/d/e/1FAIpQLSekImCUe5qeXwYA0kFSFrJZ07TneLSJcWplcQaHhshpyQUj-A/viewform) currently reports that it is closed. The owner replied “yes” to the bundled registration/rules question during this review; this plan treats registration as confirmed, while the specific rule terms remain to be captured. The public page does not provide enough rules to certify eligibility.

Before treating this as an eligible entry, the team owner must verify:

- Final team roster; registration is treated as owner-confirmed above.
- Whether existing code/assets are permitted, what must be built during the event, and how prior work must be disclosed. This repository contains substantial prior work; disclose it explicitly.
- Whether Ideogram counts as an external app, and whether the proposed Drive/Ideogram/Meta actions satisfy the requirement.
- Any sponsor-stack, open-source, licensing, residency/age, submission-channel, access, or recording conditions in the actual rules.
- Exact submission cutoff and how judges access the app/repository. Do not assume judging start is the upload deadline.

These are owner follow-ups, not reasons to delay local planning. If prior work is prohibited, seek an eligible route before reusing this foundation in the submission. Continue the beta independently if entry is unavailable.

### Three-app proof

| App | Meaningful role | Evidence to capture |
|---|---|---|
| Google Drive | List/download the selected source folder; optionally return the reviewed package to an authorized output folder | Sanitized source IDs, content hashes, download receipts; output link if uploaded |
| Ideogram | Generate a text-free background for the selected angle when generation is useful | Request metadata, provider receipt where available, generated artifact hash |
| Meta Ads | Create the approved campaign structure with a static and a video ad, with delivery disabled | Redacted payload preview, returned IDs, read-back of campaign/ad-set/ad state |

Do not count local Remotion/FFmpeg as external apps. Existing cached artwork alone does not demonstrate a new Ideogram action. Generate only when useful and authorized, then preserve the genuine run evidence for the demo. Ask the organizer about app eligibility first; if providers do not count, substitute a conventional app with a real workflow role, such as an approved campaign review record in a team's existing task tracker. That contingency adds integration work and must be decided at the eligibility gate, not during the final demo hour.

## 3. Review of the current scope and implementation

Reviewed in order: `PROJECT_MEMORY.md`, `docs/FUTURE_SCOPE.md`, `README.md`, `remotion/README.md`, and the Houston audit. Also reviewed `docs/CORE_PROJECT_FILES.md`, the source inventory, and selected orchestration, storage, critique, video-contract, and Meta code. This is a planning review; integrations and render performance were not live-tested.

| Area | Reuse | Work needed for the happy path |
|---|---|---|
| Poster | Existing structured models, local compositing, rendering, exact-copy/layout audits | Neutral manifest adapter; remove hidden Houston facts from the new path |
| Reel | EditSpec, FFmpeg preparation, Remotion primitives and component library | Manifest-to-EditSpec adapter, bounded shot selection, job integration, exported-video QA |
| Visual inspection | `openai_studio.py` already has image critique, structured findings, and token patches | Campaign-aware independent inspection, blocking severity, reel-frame review, bounded repair and revalidation |
| Persistence/UI | FastAPI studio and SQLite brand/project storage | Campaign runs, step checkpoints, questions, approvals, receipts, combined review page |
| Footage understanding | TwelveLabs probe and existing shot fixtures | Small-folder ingestion and validated shot choices; label curated/preindexed data honestly |
| Meta | Dry-run-first single-video creator with paused delivery objects | Manifest-led image + video payloads, explicit configuration, approval checks, reconciliation and read-back |
| Evaluation | Existing poster/storage/provider/web tests | Cross-app journey, fault cases, video checks and submission evidence |

Scope corrections:

1. Move evaluation and basic recovery from P1 into the first implementation slice. They are necessary to show the workflow works.
2. Keep both poster and reel, but reduce breadth to one selected angle, one layout per format, a 15–25-second reel, and a small asset folder. Two proposed angles can be text choices; producing both doubles work unnecessarily.
3. Support one bounded correction, such as moving the CTA or enlarging the phone. Arbitrary canvas editing, extensive shot search, and optional voiceover can wait.
4. Separate creative readiness from deployment readiness. Missing budget can block Meta preparation without preventing a clearly labeled creative draft. Unconfirmed offer/deadline/contact must never become approved factual copy.
5. Preserve extraction's exact-source behavior. Add creative copywriting as an explicit proposal stage grounded in approved facts; do not silently change the existing extraction contract.

Documentation conflicts found: memory still frames the product as cricket-specific while the current scope is generic; treat cricket as the implemented adapter. The scope overstates the absence of visual critique; there is a starter interface, not a complete independent QA loop. Current `git status` shows a smaller set of untracked legacy files than the memory suggests; use actual status when preparing a baseline. UTF-8 reads render the reviewed README correctly, so a broad encoding cleanup is not justified by terminal mojibake.

Operational conflicts remain real: the Meta creator hardcodes the older phone, an older video, a $40 lifetime default, four days, and new-form creation. Replace implicit defaults in the new path with reviewed manifest fields. The September 15 offer expires shortly after the event; beta campaigns need freshly confirmed dates. A historical $25/day for 14 days proposal must not silently become this campaign's budget or extend an expired offer.

## 4. Exact happy path and definition of done

1. **Start:** owner enters a rough request and selects an accessible Drive folder with a logo, a few photos and 3–6 short clips. A connection preflight confirms access and supported media.
2. **Ground:** agent inventories sources and drafts a versioned manifest. Conflicting operational facts are visible with their source; the owner resolves one material question. Imported text is evidence, never permission to operate tools.
3. **Plan:** agent proposes two short angles, chooses/recommends one, and produces exact copy plus bounded image and video plans. The owner can inspect the facts without retyping them.
4. **Produce:** create/reuse approved text-free artwork and deterministically compose 1080x1350 PNG; validate clip ranges and render 1080x1920 MP4 with approved music and muted camera audio where required.
5. **Check:** deterministic checks and an independent rendered-media inspection generate structured findings. Repair the responsible layer once or twice, then recheck; unresolved blockers stop approval.
6. **Correct:** owner requests a supported change. Show a before/after version, changed properties and fresh QA. Previous QA/approval cannot apply to changed content.
7. **Review:** display poster, playable reel, copy, dates, audience, budget, form/destination and QA. Generate a read-only payload preview. Capture explicit authorization to create exactly that package.
8. **Prepare:** create one campaign, one ad set and two ads referencing their respective creatives. Campaign, ad set and ads are PAUSED and verified by read-back; creative/media objects are linked by ID and are not described as having delivery status.
9. **Finish:** owner can download the package and see receipts, checks, remaining limitations and the paused result. No activation tool is exposed in the hackathon/beta journey.

Done means one run completes through the UI without hand-editing JSON, calling undocumented commands, or copying facts between stages. An operator may authorize external creation; authorization is a product step, not manual plumbing. A second clean run must also complete. Historical artifacts are regression references, not evidence that this new journey already works.

## 5. Implementation design

Use the current FastAPI app and Python package, with additive campaign modules and a thin adapter into Remotion. Avoid a frontend rewrite, package renaming, a distributed agent framework, or new infrastructure before the integrated path works.

Proposed boundaries (new files, not existing capabilities):

| Boundary | Responsibility |
|---|---|
| `campaign_models.py` | CampaignManifest, facts/provenance, AssetRef, Artifact, QAReport, Approval, ToolReceipt |
| `campaign_runner.py` | Persisted state transitions, question gate, bounded tool selection, retries/resume |
| `campaign_adapters/` | Drive intake, poster mapping, video plan/preparation/render, Meta payload builder/executor |
| `campaign_qa.py` | Deterministic checks, separate inspector call, repair routing |
| `storage.py` additions | Runs, step attempts, artifact versions, approval hashes, external object ledger |
| `web.py` and web templates additions | Brief, pending question, progress/trace, combined review and package export |
| `tests/campaign/` and versioned evaluation fixtures | Contracts, adversarial inputs, recovery, approval and integration evidence |

Manifest fields: business/brand, campaign purpose, source references, factual values with source/status, timezone-aware offer and delivery dates, exact approved copy, audience, destination/form, budget type/currency/amount, media/audio permissions, selected angle, asset hashes, and schema version. Keep artifacts and tool receipts in linked records rather than an ever-growing prompt.

State path: `intake -> needs_facts -> ready_to_plan -> producing -> checking -> needs_review -> approved_for_paused_create -> creating -> paused_verified`. Also persist `blocked`, `failed`, and `partial_external_result`; resuming uses completed step outputs. Trace entries show decisions, source references, tool inputs/outputs and outcomes, not private model reasoning.

The agent handles ambiguity, angle choice, shot selection and constrained repair. Code validates its structured decisions and enforces permissions. For hackathon footage selection, rank a small candidate set with timestamps and thumbnails; validate every chosen range. If indexing is not ready, permit a visibly labeled reviewed candidate list. Do not claim autonomous footage discovery from a hand-authored EditSpec.

Reliability rules:

- Cache by source hash + manifest revision + tool/configuration version. A factual change invalidates dependent artifacts and approvals; a layout-only change need not regenerate artwork.
- Bind creation approval to the exact manifest, creative hashes and payload preview. Any relevant edit requires review again. Require known paused parents; do not reuse an arbitrary existing ad set.
- Journal intent before external writes and receipts immediately afterward. A timed-out write has unknown outcome: reconcile before retrying; if ambiguous, stop for inspection. Local deduplication is not a claim of provider-level exactly-once delivery.
- Retry transient reads with bounded backoff. Cap repairs at two and paid generation attempts at an explicit configured limit. Show actionable failure and resume controls.
- Reject instructions embedded in Drive content that request token access, tool execution, publishing or approval bypass. Keep credentials server-side; sanitize logs and demo sources.
- Validate allowed input types, file-size/duration limits and subprocess arguments. Do not interpolate source text into shell commands.

## 6. Phases and delivery gates

### Phase 0 — eligibility, access and baseline

Before the event: confirm rules/registration, disclose the baseline, choose permission-cleared demo media, and verify the intended account/page/form and provider access. Prepare an honest existing-versus-event-built inventory. Do pre-event implementation only if the rules permit it.

Run the existing offline test suite and representative poster/reel rebuild; measure cold/warm render times. Review tracked changes and private/generated assets before any commit. Keep credentials and children's private media out of the public submission.

**Gate:** eligible entry route known; three-app interpretation known; supported assets available; renderer works; external access risks identified. If an account cannot create paused objects, a dry-run demo remains useful but does not meet our full product completion claim.

### Phase 1 — integrate the narrow vertical slice

Build the manifest and state store first, then Drive intake and adapters into the existing renderers. Start the Meta payload adapter early enough to expose API/account incompatibilities, using offline payload checks and authorized smoke tests. Wire one run through the existing web app.

**Gate:** a source folder produces both downloadable outputs and the corresponding payload preview, all from one manifest revision. No hidden fixture contact, logo, offer or budget leaks into a new business.

### Phase 2 — make trust visible

Add rendered-media inspection, one bounded correction, approval invalidation, tool receipts and resume. Generalize paused publishing to both formats; after explicit authorization, read back created delivery states. Add fault tests while building each boundary.

**Gate:** two complete runs, one demonstrated repaired failure, one interrupted/resumed run, zero unauthorized writes in tests, and verified paused state for the authorized live integration case.

### Phase 3 — freeze and submit

Run the evaluation matrix, preserve result files, record the real end-to-end run, and produce the demo and short reliability brief. Smoke-test the judge setup from clean instructions and inspect the submission for private data.

**Gate:** working access/repository, playable two-minute recording, system/reliability brief, provenance/baseline disclosure, dependency/setup instructions, evaluation results and known limitations. Verify any additional organizer requirements before submitting.

### Event-day allocation

The [published schedule](https://multiappagenthackathon.com/) starts opening at 09:00 Pacific, building at 09:30, judging at 16:00, and awards at 16:40. Houston is two hours ahead on this date. The blocks below are our proposed allocation, not organizer deadlines.

| Houston time, September 13 | Work and stop condition |
|---|---|
| 11:00–11:30 | Opening; settle rule changes and freeze scope |
| 11:30–12:15 | Manifest, persisted runner, access preflight and minimal Drive intake |
| 12:15–13:30 | Connect poster/reel adapters and start long media/provider jobs |
| 13:30–14:15 | Integrated review and Meta preview; authorized integration verification |
| 14:15–15:15 | Independent QA, bounded repair, approval/version gate |
| 15:15–16:15 | Fault suite, resume verification, second complete run |
| 16:15–17:00 | Freeze features; record demo and package evidence |
| 17:00–17:30 | Check submission/access and submit if the actual cutoff permits |
| 17:30–18:00 | Buffer before published judging start |

This is aggressive for a solo builder starting with today's integration gaps. It is a timebox, not a feasibility guarantee. If the first integrated run is not available by 14:15, cut layout variety, free-form spatial editing, optional voiceover, broad footage search and UI decoration. Keep both formats, meaningful app actions, approval enforcement and honest evidence. If those cannot fit, submit the actual working subset with limitations; do not present mocked completion as full success.

If 2–4 human builders are available, assign contract/orchestration, media/QA, integrations/recovery, and UX/evaluation/demo ownership. Agree contracts first; integrate hourly. With fewer people, combine adjacent roles and retain one integration owner.

### Phase 4 — beta MVP 1, proposed September 14–27

First week: harden the workflow with real users. Generalize brand/copy assumptions; add a second business fixture, clearer missing-input handling, durable background jobs with restart recovery, progress/cancellation, cost/time reporting and a packaged local or managed pilot deployment. Replace expired campaign offers. Invite 3–5 permission-cleared design partners; explicitly support small folders, a fixed set of layouts and one Meta objective/form workflow.

Second week: fix pilot failures and prepare controlled access. Before sharing a hosted multi-customer service, implement authentication, tenant isolation, server-side encrypted credentials or managed secret storage, least-privilege app connections, disconnect/revocation, retention/deletion, backups with a restore check, basic error monitoring and a support runbook. If those gates are unfinished, use isolated operator-assisted installations and label the beta accordingly. Verify current provider permissions and distribution requirements before enabling self-service connections.

**Beta gate:** at least five pilot campaigns across at least two businesses; at least four complete within the declared supported-input envelope without developer intervention beyond documented onboarding and user approvals; both formats pass QA; every material correction refreshes approval; no cross-tenant exposure or unauthorized external action; restart and duplicate-click cases pass. Proposed usability target: median owner interaction below ten minutes, excluding provider/render wait; report actual elapsed latency and cost separately. These are release targets, not current results.

Do not launch broadly to meet the calendar if the gates fail. Keep activation manual/outside the product and track each campaign's creative IDs and review outcome. Qualified-lead and enrollment reporting is a later expansion; historical raw CPL does not validate this product's impact.

### Phase 5 — after beta evidence

Prioritize from observed pilot friction: more business templates, better shot selection/captions, approval roles, reliable distribution, then outcome feedback linking leads to qualified inquiries/trials/enrollments. Add voiceover, broad analytics or autonomous optimization only when demand and controls justify the work. Validate willingness to pay through pilots before building billing or a large marketing suite.

## 7. Evaluation and proof package

Use 16 versioned scenarios. Most run offline with deterministic fixtures and mocked providers; separately report real-provider integration runs. Do not merge mocked and live success into a single misleading percentage.

| # | Scenario | Required result |
|---:|---|---|
| 1 | Complete supported brief and mixed folder | Both assets and matching preview produced |
| 2 | Missing offer or conflicting phone | Material question; unresolved fact never published |
| 3 | Expired deadline or incompatible delivery dates | Block affected approval until corrected |
| 4 | Owner declines a free offer | No free-trial claim in any artifact or payload |
| 5 | Missing logo or unusable footage | Explain missing input; never mark both-format delivery complete |
| 6 | Different small-business brand | No inherited cricket/Houston facts or assets |
| 7 | Long copy, overflow or obstructed CTA | Detect; local repair or explicit escalation |
| 8 | QR and destination disagree | Block until destinations agree and are rechecked |
| 9 | Generated artwork has stray text/visual defect | Inspector flags seeded defect; bounded repair/escalation |
| 10 | Weak reel hook or unreadable end card | Frame review flags issue and verifies revised frames |
| 11 | Camera audio/music provenance violates policy | Audio graph/provenance gate blocks; inspect exported playback |
| 12 | Supported spatial correction | New artifact version, fresh checks, prior approval invalidated |
| 13 | Drive/provider read timeout or render crash | Bounded retry/resume; no fabricated output |
| 14 | Duplicate click or Meta write timeout | Reuse confirmed result or reconcile; no blind duplicate create |
| 15 | Activation request, stale approval or source prompt injection | Reject unauthorized operation; no write side effect |
| 16 | Authorized live paused creation of both ads | Receipts and read-back verify intended delivery objects paused |

Each result records expected/actual behavior, manifest/artifact revisions, failure reason, repair count, latency, provider costs when available, and whether the case was mocked, live, skipped or blocked. Count a correct escalation as a pass only when the expected result requires escalation. A happy-path case that escalates is not completion.

Record image dimensions, exact-copy ownership/coverage, overflow, contrast, URL/QR checks, and logo loading. For video, validate EditSpec ranges and duration, inspect ffprobe output, opening/end/overlay-transition frames, and play the MP4. Camera-track exclusion can be checked structurally; representative frames cannot prove absence of voices or all temporal defects. Keep human playback and music provenance explicit until stronger audio QA exists.

For inspector credibility, use separately labeled clean and defective examples; report detected defects, missed defects and false alarms. The inspector receives final assets and manifest requirements in a separate call, not the producer's self-assessment. Independence is procedural, not a guarantee that the model is correct.

Proposed submission gate: all permission, factual-blocking and duplicate-write tests pass; both supported end-to-end repetitions pass; remaining evaluation failures/skips disclosed. No invented pass rate. Bundle a sanitized manifest, run trace, before/after QA, evaluation JSON/summary, PNG, MP4 and external receipts. Keep replay material clearly labeled as a recorded genuine run rather than live execution.

## 8. Winning presentation and submission brief

The rubric in section 2 favors execution and reliability together. Allocate engineering effort accordingly: a complete path plus a recovered failure is stronger evidence than additional templates.

| Demo time | Show |
|---|---|
| 0:00–0:12 | Owner problem and rough brief with Drive inputs |
| 0:12–0:28 | One fact conflict resolved, with provenance visible |
| 0:28–0:50 | Final poster and playable reel; genuine provider/action trace |
| 0:50–1:15 | One visible defect/correction, local repair and new QA result |
| 1:15–1:40 | Approved payload, actual Meta receipts and verified paused state |
| 1:40–2:00 | Evaluation outcomes, one recovery example and final customer benefit |

Use a pre-recorded genuine run if long provider jobs prevent a real-time presentation; disclose time compression and caching. Keep an offline replay for network failure, but do not count replay as a fresh integration test. Show real measurements rather than fabricated time saved, lead lift or revenue. The Houston audit supplies domain motivation, not proof that ADvantage improves campaign performance.

The short system/reliability brief should explain the customer problem; three app roles; architecture and agent decisions; pre-existing versus event-built work; manifest/approval/recovery design; evaluation counts with denominators and live/mock separation; observed time/cost; limitations; and exact judge setup. Include a short diagram only if it makes those boundaries clearer.

## 9. Immediate execution order

1. Owner captures rule terms and settles app counting, team capacity and beta timing.
2. Builder inventories the baseline and verifies offline renders/tests and external access.
3. Freeze the single supported demo scenario and CampaignManifest contract.
4. Connect Drive, poster, reel and Meta preview through one persisted run.
5. Add visible QA/repair, version-bound approval and verified paused creation.
6. Run the fault suite and two complete repetitions; freeze and submit evidence.
7. Use pilot failures to drive the private-beta work, with security and reliability gates before shared deployment.

The next implementation deliverable should be the manifest-driven vertical slice, not another standalone creative experiment.

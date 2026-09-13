# Demo runbook — the happiest happy path

Every value below has been run end to end against the real services on this
machine (Ideogram, OpenAI, the live Meta ad account, and the real Google Drive
folder). Timings are measured, not estimated.

The one rule: **pre-render the reel before you present.** Everything else is
safe to do live.

---

## Pre-flight (do this 15 minutes before)

Run in order and confirm each line before moving on.

```powershell
cd C:\Users\pavan\Desktop\ADvantage
uv sync --group video          # imageio-ffmpeg is NOT in the base install; the reel fails without it
.\.venv\Scripts\python.exe -m pytest tests -q
```

```powershell
# Terminal 1 — backend
cd C:\Users\pavan\Desktop\ADvantage
.\.venv\Scripts\cricket-posts.exe serve
```

```powershell
# Terminal 2 — frontend
cd C:\Users\pavan\Desktop\ADvantage\frontend
npm run dev
```

Then open <http://localhost:3000>.

**Smoke check** — paste into a third terminal. All three must pass:

```powershell
cd C:\Users\pavan\Desktop\ADvantage
.\.venv\Scripts\python.exe -c "import requests as r; print('palettes', r.get('http://127.0.0.1:8000/api/campaigns/palettes').status_code)"
.\.venv\Scripts\python.exe -c "import requests as r; print('drive   ', r.get('http://127.0.0.1:8000/api/campaigns/drive/folders').status_code)"
```

Expect `palettes 200` and `drive 200`. If Drive returns **503**, its refresh
token expired — re-run `scripts\intake\google_drive_authorize.py` and update
`.env`. The app still works on file uploads if you skip Drive entirely.

### Things that will bite you

| Risk | Why | Guard |
|---|---|---|
| Running from `ADvantage-ui` | Sibling checkout with old code; server starts but new routes 405 | Always `cd ADvantage` |
| `imageio-ffmpeg` missing | Reel render dies at the probe step | `uv sync --group video` |
| Port 8000/3000 in use | A stray server from an earlier run | `Get-NetTCPConnection -LocalPort 8000 -State Listen \| ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }` |
| Rendering a reel live | 4 minutes of dead air | Pre-render (below) |

---

## Demo 1 — Poster, live (~40 seconds total)

Safe to run in front of people. Ideogram generation is ~23s; the whole request
returns in about 35–40s.

### Step 1 — Brief

| Field | Paste exactly this |
|---|---|
| Format | **Poster** |
| Business name | `22 Yards Houston Cricket Academy` |
| Brief | `We are starting our new under 13 academy. Small groups, qualified coaches, and a focus on fundamentals, balance and confidence. First session free if you sign up before September 30.` |
| Logo | *(skip — optional, and skipping is one less thing to go wrong)* |

The brief is doing real work here: the agent extracts the offer and the
benefits from it, so write it as prose, not keywords. That extraction is the
thing worth narrating.

### Step 2 — The agent's questions

It will say something like *"I pulled the offer and core benefits from your
brief; I just need your preferred poster look."* and show what it already
filled in. **Talk over this bit** — it is the most impressive screen.

It asks 2 questions and pre-fills both:

| Question | Answer |
|---|---|
| Art style | **Warm lifestyle** (usually pre-selected — just accept it) |
| Artwork scene | Accept the drafted answer, or paste: `Young children batting and fielding on a green practice ground at golden hour, coach guiding a small group, warm natural light` |

Click **Looks good — continue**.

### Step 3 — Budget & destination

| Field | Paste exactly this |
|---|---|
| Contact phone | `5715388147` |
| Destination URL | `https://axon22yards.com/join?location=houston` |
| Offer text | `Free trial classes ending Sept 30` |
| Audience | `Parents of players aged 5 to 13` |
| Budget (USD) | `40` |
| Campaign days | `4` |

Submit. ~40 seconds.

### What to point at on the review screen

1. **The poster** — the benefits appear as bullets because the agent pulled
   them out of the brief. Nobody typed them.
2. **How this turned out** — what was made, why, and *Information included*,
   which lists every line actually on the artwork.
3. **What the agent did** — the real timed step log.
4. **Meta ad preview + why this campaign** — the rationale is grounded in a
   live read of the real ad account, and says so.
5. **Regenerate** — type `make it bolder and show more players on the field`,
   pick a different colour scheme, hit Regenerate. This makes a *new* run and
   keeps the old one. (~40s, safe to do live.)

**Do not click "Create paused campaign"** unless you intend to create real
objects in the Meta account.

---

## Demo 2 — Reel, pre-rendered (render takes ~4 minutes)

A reel render is 200–240 seconds and the request blocks for all of it. Render
it **before** you present, then just open the URL.

### Pre-render (run ~10 minutes before)

```powershell
cd C:\Users\pavan\Desktop\ADvantage
.\.venv\Scripts\python.exe scripts\demo\prebake_reel.py
```

It prints a `/campaigns/<id>` URL. Keep that tab open. Runs live in the same
server process the UI is talking to, so the page just works.

### If you must do it live in the UI

Same three steps, with these values:

| Field | Value |
|---|---|
| Format | **Reel** |
| Business name | `22 Yards Houston Cricket Academy` |
| Brief | *(same as the poster)* |
| Footage | **Use my Google Drive** → `Social Media / Cricket` |
| Reel feel | **High energy** (pre-selected) |
| Contact phone | `5715388147` |
| Destination URL | `https://axon22yards.com/join?location=houston` |
| Offer text | `Free trial classes ending Sept 30` |
| Audience | `Parents of players aged 5 to 13` |
| Budget / days | `40` / `4` |

Measured result: **1080×1920, 16.85s, verification passed**, built from 6
clips with an 8-beat overlay arc.

---

## Measured timings

| Step | Time |
|---|---|
| Interview round (per round) | 3–8s |
| Poster — Ideogram + stamp + review | ~35–40s |
| Reel — full render | 200–240s |
| Drive folder list | <2s |
| Drive import (Cricket, 6 clips) | ~30s |

---

## Known limits — say these before someone asks

- **Drive import caps at 6 videos** per folder (`DriveIntakeConfig.max_videos`).
  The Cricket folder has 32 files; 26 report `video_limit_reached`. Deliberate,
  not a failure.
- **Runs live in memory.** Restarting the backend loses every run and its URL.
  Don't restart between the pre-render and the demo.
- **The reel critique does not watch the video.** It reviews the edit plan and
  file checks only, and says so.
- **No background job queue.** One generate at a time; a second submit while a
  reel renders will queue behind it.

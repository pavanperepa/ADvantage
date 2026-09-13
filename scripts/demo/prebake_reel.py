"""Render the demo reel ahead of time and print the URL to open during the demo.

A reel render blocks for 200-240 seconds. Doing that live is four minutes of
dead air in front of an audience, so this renders it in advance against the
*running* backend -- the same process the browser is talking to -- and prints
the review URL to keep open in a tab.

Run it about ten minutes before presenting:

    .venv\\Scripts\\python.exe scripts\\demo\\prebake_reel.py

Both servers must already be up (see docs/DEMO_RUNBOOK.md). It does not touch
Meta: `run_campaign` only builds a read-only preview, and creating paused
objects stays a separate, explicitly-clicked action.
"""

from __future__ import annotations

import argparse
import sys
import time

import requests

DEFAULT_API = "http://127.0.0.1:8000"
DEFAULT_UI = "http://localhost:3000"
DEFAULT_FOLDER = "cricket"

BRIEF = (
    "We are starting our new under 13 academy. Small groups, qualified coaches, "
    "and a focus on fundamentals, balance and confidence. First session free if "
    "you sign up before September 30."
)

FORM = {
    "business_name": "22 Yards Houston Cricket Academy",
    "brief_text": BRIEF,
    "format": "reel",
    "contact_phone": "5715388147",
    "destination_url": "https://axon22yards.com/join?location=houston",
    "offer_text": "Free trial classes ending Sept 30",
    "audience": "Parents of players aged 5 to 13",
    "budget_usd": "40",
    "campaign_days": "4",
    "reel_feel": "high_energy",
    "palette": "academy_blue",
    "proof_point": "Coaches certified by the state association",
}

BENEFITS = [
    "Small groups with qualified coaches",
    "Build fundamentals and coordination",
    "Play matches when ready",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default=DEFAULT_API, help="Backend base URL")
    parser.add_argument("--ui", default=DEFAULT_UI, help="Frontend base URL")
    parser.add_argument(
        "--folder",
        default=DEFAULT_FOLDER,
        help="Substring of the Drive subfolder name to use (default: cricket)",
    )
    args = parser.parse_args()

    try:
        response = requests.get(f"{args.api}/api/campaigns/drive/folders", timeout=30)
    except requests.RequestException as exc:
        print(f"Could not reach the backend at {args.api}: {exc}")
        print("Start it first:  .venv\\Scripts\\cricket-posts.exe serve")
        return 1

    if response.status_code == 503:
        print("Google Drive is not authorized, so there is no footage to build a reel from.")
        print("Run scripts\\intake\\google_drive_authorize.py and update .env, then retry.")
        return 1
    if response.status_code != 200:
        print(f"Listing Drive folders failed ({response.status_code}): {response.text[:300]}")
        return 1

    folders = response.json()
    match = next((f for f in folders if args.folder.lower() in f["name"].lower()), None)
    if match is None:
        print(f"No Drive folder matching {args.folder!r}. Available:")
        for folder in folders:
            print(f"  - {folder['name']}")
        return 1

    print(f"Using footage from: {match['name']}")
    print("Rendering. This takes 200-240 seconds -- leave it running.")

    started = time.monotonic()
    try:
        created = requests.post(
            f"{args.api}/api/campaigns",
            data={**FORM, "drive_folder_id": match["id"]},
            files=[("key_benefits", (None, benefit)) for benefit in BENEFITS],
            timeout=900,
        )
    except requests.RequestException as exc:
        print(f"The render request failed: {exc}")
        return 1

    elapsed = time.monotonic() - started
    if created.status_code != 201:
        print(f"Generation failed ({created.status_code}) after {elapsed:.0f}s:")
        print(created.text[:600])
        return 1

    run = created.json()
    artifact = run["artifact"]
    print(f"\nDone in {elapsed:.0f}s.")
    print(
        f"  {artifact['width']}x{artifact['height']}  "
        f"{artifact['duration_seconds']:.1f}s  "
        f"verification passed: {run['verification']['passed']}"
    )
    print(f"\n  OPEN THIS TAB:  {args.ui}/campaigns/{run['id']}\n")
    print("Runs live in memory -- do not restart the backend before the demo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

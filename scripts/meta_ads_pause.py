"""Pause specific Meta ad objects by ID, and verify the change stuck.

Deliberately takes explicit IDs only. There is no "pause everything" mode, so
this cannot take down more than what you name on the command line.

    python scripts/meta_ads_pause.py 120250067045430337 120250067045420337
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
GRAPH_ROOT = "https://graph.facebook.com"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="+", help="Campaign, ad set, or ad IDs to pause")
    parser.add_argument("--status", default="PAUSED", choices=["PAUSED", "ACTIVE"])
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    token = os.environ.get("META_ACCESS_TOKEN")
    if not token:
        raise SystemExit("META_ACCESS_TOKEN must be set in .env")
    base = f"{GRAPH_ROOT}/{os.environ.get('META_API_VERSION', 'v24.0')}"

    failures = 0
    for object_id in args.ids:
        response = requests.post(
            f"{base}/{object_id}",
            data={"status": args.status, "access_token": token},
            timeout=60,
        ).json()
        if "error" in response:
            print(f"  {object_id}  FAILED: {response['error'].get('message')}")
            failures += 1
            continue

        check = requests.get(
            f"{base}/{object_id}",
            params={"fields": "id,name,status,effective_status", "access_token": token},
            timeout=30,
        ).json()
        state = check.get("effective_status", "?")
        mark = "ok" if check.get("status") == args.status else "MISMATCH"
        print(f"  {object_id}  {check.get('status','?'):<8} effective={state:<10} {mark}"
              f"  {check.get('name','')[:38]}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

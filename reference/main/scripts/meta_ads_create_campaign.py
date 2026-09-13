"""Create one Houston lead campaign programmatically, paused, from a video reel.

Mirrors the structure that actually worked in this account (see
``output/meta_ads_houston/HOUSTON_META_ADS_AUDIT.md`` and the corrected read in
memory): broad targeting with no interest stacking, a 15-mile radius on the
venue, lifetime budget at campaign level, highest-volume bidding, and an
instant form on the ad.

Everything is created PAUSED. Nothing spends until you unpause it in Ads
Manager. The default mode is a dry run that prints the exact payloads without
touching the account; pass ``--execute`` to actually create the objects.

Credentials come from the repository's ignored ``.env``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[3]
GRAPH_ROOT = "https://graph.facebook.com"
DEFAULT_API_VERSION = "v24.0"

PAGE_ID = "346097132754442"
# 22 Yards / Smaash Indoor Cricket & Baseball Club, from the historical ad sets.
VENUE_LAT = 29.717083446227
VENUE_LNG = -95.653278515305
VENUE_RADIUS_MILES = 15

# The workhorse form: 113 leads, FULL_NAME / PHONE / EMAIL / ZIP. Immutable,
# and its thank-you screen exits to Instagram rather than anywhere useful.
PROVEN_FORM_ID = "1258789453108859"

PRIVACY_POLICY_URL = "https://22yardshouston.com/privacy-policy/"
BUSINESS_PHONE = "+17135709054"

DEFAULT_VIDEO = ROOT / "output" / "reel-lab" / "academy-intro-remotion-v7-natural-ending.mp4"

# Primary text. Every factual claim here is recycled from this account's own
# previously published ad copy in creatives.csv. Do not add schedules, prices,
# or age bands unless the business has confirmed them.
PRIMARY_TEXT = """\
Houston parents — this is how we actually coach. \U0001f3cf

Show. Correct. Apply. That's the loop every young player runs at 22 Yards \
Houston — age-appropriate training with certified coaches, indoors, so \
weather never cancels a session.

Structured coaching and real reps. Not generic drills.

\U0001f449 New players get a free trial session. Tell us your child's age and \
we'll call you back to book it."""

# Swap in if the free trial is not authorised:
PRIMARY_TEXT_NO_OFFER = """\
Houston parents — this is how we actually coach. \U0001f3cf

Show. Correct. Apply. That's the loop every young player runs at 22 Yards \
Houston — age-appropriate training with certified coaches, indoors, so \
weather never cancels a session.

Structured coaching and real reps. Not generic drills.

\U0001f449 Tell us your child's age and we'll call you back with squad times, \
availability, and pricing."""

HEADLINE = "Youth Cricket Coaching — Houston"
CALL_TO_ACTION = "SIGN_UP"  # $5.52 historically, vs $8.74 for LEARN_MORE.


class Graph:
    """Thin Graph API wrapper that fails loudly and never logs the token."""

    def __init__(self, token: str, version: str, account_id: str, dry_run: bool) -> None:
        self.token = token
        self.base = f"{GRAPH_ROOT}/{version}"
        self.account = f"act_{account_id}"
        self.dry_run = dry_run

    def get(self, path: str, **params: Any) -> dict:
        params["access_token"] = self.token
        response = requests.get(f"{self.base}/{path}", params=params, timeout=60)
        return self._unwrap(response)

    def post(self, path: str, files: Any = None, token: str | None = None,
             **payload: Any) -> dict:
        printable = {k: v for k, v in payload.items()}
        print(f"\n  POST {path}")
        print("  " + json.dumps(printable, indent=2)[:2000].replace("\n", "\n  "))
        if self.dry_run:
            return {"id": f"<dry-run:{path}>"}
        payload["access_token"] = token or self.token
        response = requests.post(
            f"{self.base}/{path}", data=payload, files=files, timeout=600
        )
        return self._unwrap(response)

    def page_token(self) -> str:
        """Page-scoped token; required for lead form creation."""
        pages = self.get("me/accounts", fields="id,name,access_token").get("data", [])
        for page in pages:
            if page["id"] == PAGE_ID:
                return page["access_token"]
        raise SystemExit(f"Page {PAGE_ID} not available on this token")

    @staticmethod
    def _unwrap(response: requests.Response) -> dict:
        try:
            body = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        if "error" in body:
            error = body["error"]
            raise SystemExit(
                f"Graph API error {error.get('code')}/{error.get('error_subcode')}: "
                f"{error.get('message')}\n{error.get('error_user_msg') or ''}"
            )
        return body


def upload_video(graph: Graph, path: Path) -> str:
    """Upload the reel and block until Meta finishes transcoding it."""
    if not path.exists():
        raise SystemExit(f"Video not found: {path}")
    size_mb = path.stat().st_size / 1_048_576
    print(f"\nUploading {path.name} ({size_mb:.1f} MB)...")
    with path.open("rb") as handle:
        created = graph.post(
            f"{graph.account}/advideos",
            files={"source": (path.name, handle, "video/mp4")},
            name=path.stem,
        )
    video_id = created["id"]
    if graph.dry_run:
        return video_id

    for attempt in range(60):
        status = graph.get(video_id, fields="status").get("status", {})
        state = status.get("video_status")
        if state == "ready":
            print(f"  video {video_id} ready")
            return video_id
        if state == "error":
            raise SystemExit(f"Video processing failed: {status}")
        print(f"  processing ({state})... {attempt * 10}s")
        time.sleep(10)
    raise SystemExit("Timed out waiting for video processing")


def pick_thumbnail(graph: Graph, video_id: str) -> str | None:
    """Meta requires a thumbnail for video creatives; prefer its own pick."""
    if graph.dry_run:
        return "<dry-run:thumbnail>"
    thumbs = graph.get(f"{video_id}/thumbnails").get("data", [])
    if not thumbs:
        return None
    preferred = next((t for t in thumbs if t.get("is_preferred")), thumbs[0])
    return preferred.get("uri")


def create_lead_form(graph: Graph) -> str:
    """Clone the proven 4-question form, but end on a call button.

    Meta locks a form permanently once it takes its first lead, so the existing
    form's thank-you link (which points at Instagram) cannot be edited. Same
    questions and same friction as the proven form; it just ends somewhere that
    converts instead of a dead end. No second form for the parent to fill in.
    """
    created = graph.post(
        f"{PAGE_ID}/leadgen_forms",
        token=graph.page_token() if not graph.dry_run else None,
        name=f"HOU_ACADEMY_FREETRIAL_{datetime.now():%Y%m%d}",
        locale="en_US",
        questions=json.dumps(
            [{"type": "FULL_NAME"}, {"type": "PHONE"},
             {"type": "EMAIL"}, {"type": "ZIP"}]
        ),
        privacy_policy=json.dumps(
            {"url": PRIVACY_POLICY_URL, "link_text": "Privacy Policy"}
        ),
        thank_you_page=json.dumps(
            {
                "title": "Thanks! We'll call you soon.",
                "body": "We'll call to book your child's free trial session "
                        "at 22 Yards Houston.",
                "button_type": "CALL_BUSINESS",
                "button_text": "Call us now",
                "business_phone_number": BUSINESS_PHONE,
                "country_code": "US",
            }
        ),
    )
    print(f"  lead form {created['id']} created")
    return created["id"]


def build_targeting() -> dict:
    """Broad, no interests. Interest stacking cost $17.23/lead in this account."""
    return {
        "age_min": 18,
        "age_max": 65,
        "geo_locations": {
            "location_types": ["home", "recent"],
            "custom_locations": [
                {
                    "latitude": VENUE_LAT,
                    "longitude": VENUE_LNG,
                    "radius": VENUE_RADIUS_MILES,
                    "distance_unit": "mile",
                    "country": "US",
                }
            ],
        },
        # Matches targeting_automation on all 11 historical ad sets.
        "targeting_automation": {"advantage_audience": 1},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget", type=float, default=40.0, help="Lifetime budget in USD")
    parser.add_argument("--days", type=int, default=4, help="Run length in days")
    parser.add_argument("--video", type=Path, default=DEFAULT_VIDEO)
    parser.add_argument(
        "--form-id",
        default=None,
        help=f"Reuse an existing form (e.g. {PROVEN_FORM_ID}). Default: create a new one.",
    )
    parser.add_argument(
        "--name",
        default=f"HOU_LEADS_ACADEMY_BROAD_{datetime.now():%Y%m%d}",
        help="Campaign name; keep the HOU_LEADS_<PROGRAM>_<AUDIENCE>_<DATE> convention",
    )
    parser.add_argument("--video-id", default=None,
                        help="Reuse an already-uploaded video instead of re-uploading")
    parser.add_argument("--adset-id", default=None,
                        help="Reuse an existing ad set; skips campaign and ad set creation")
    parser.add_argument(
        "--no-offer",
        action="store_true",
        help="Use the copy variant with no free-trial promise",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create the objects. Without this, prints payloads only.",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    token = os.environ.get("META_ACCESS_TOKEN")
    account_id = os.environ.get("META_AD_ACCOUNT_ID")
    if not token or not account_id:
        raise SystemExit("META_ACCESS_TOKEN and META_AD_ACCOUNT_ID must be set in .env")

    graph = Graph(token, os.environ.get("META_API_VERSION", DEFAULT_API_VERSION),
                  account_id, dry_run=not args.execute)

    mode = "EXECUTE" if args.execute else "DRY RUN"
    body = PRIMARY_TEXT_NO_OFFER if args.no_offer else PRIMARY_TEXT
    start = datetime.now(timezone.utc) + timedelta(minutes=15)
    end = start + timedelta(days=args.days)

    print("=" * 72)
    print(f"{mode}: {args.name}")
    print(f"  ${args.budget:.2f} lifetime over {args.days} days "
          f"(~${args.budget / args.days:.2f}/day)")
    print(f"  form {args.form_id or 'NEW'} | CTA {CALL_TO_ACTION} | all objects PAUSED")
    print("=" * 72)

    form_id = args.form_id or create_lead_form(graph)
    video_id = args.video_id or upload_video(graph, args.video)
    thumbnail = pick_thumbnail(graph, video_id)

    if args.adset_id:
        print(f"\n  reusing ad set {args.adset_id}")
        campaign = {"id": "<reused>"}
        adset = {"id": args.adset_id}
    else:
        campaign = graph.post(
            f"{graph.account}/campaigns",
            name=args.name,
            objective="OUTCOME_LEADS",
            buying_type="AUCTION",
            bid_strategy="LOWEST_COST_WITHOUT_CAP",
            lifetime_budget=int(round(args.budget * 100)),
            special_ad_categories=json.dumps([]),
            status="PAUSED",
        )

        adset = graph.post(
            f"{graph.account}/adsets",
            name=f"{args.name}_ADSET",
            campaign_id=campaign["id"],
            optimization_goal="LEAD_GENERATION",
            billing_event="IMPRESSIONS",
            destination_type="ON_AD",
            promoted_object=json.dumps({"page_id": PAGE_ID}),
            targeting=json.dumps(build_targeting()),
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            status="PAUSED",
        )

    video_data: dict[str, Any] = {
        "video_id": video_id,
        "title": HEADLINE,
        "message": body,
        "call_to_action": {
            "type": CALL_TO_ACTION,
            "value": {"lead_gen_form_id": form_id},
        },
    }
    if thumbnail:
        video_data["image_url"] = thumbnail

    creative = graph.post(
        f"{graph.account}/adcreatives",
        name=f"{args.name}_CREATIVE",
        object_story_spec=json.dumps({"page_id": PAGE_ID, "video_data": video_data}),
        # Keep Meta from re-cropping or overlaying the composed 9:16 reel.
        degrees_of_freedom_spec=json.dumps(
            {"creative_features_spec": {"standard_enhancements": {"enroll_status": "OPT_OUT"}}}
        ),
    )

    ad = graph.post(
        f"{graph.account}/ads",
        name=f"{args.name}_AD",
        adset_id=adset["id"],
        creative=json.dumps({"creative_id": creative["id"]}),
        status="PAUSED",
    )

    print("\n" + "=" * 72)
    print(f"campaign {campaign['id']}\nad set   {adset['id']}\ncreative {creative['id']}\nad       {ad['id']}")
    if graph.dry_run:
        print("\nDry run only. Re-run with --execute to create these objects.")
    else:
        print("\nCreated PAUSED. Review in Ads Manager, then unpause to start delivery.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())

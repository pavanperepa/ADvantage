"""Monitor one live campaign against the thresholds from the Houston history.

Read-only. Prints delivery, cost, and lead numbers, then judges them against
the kill criteria agreed for this run:

  * 0 leads after $20 spent
  * link CTR under 1.0% once past 3,000 impressions
  * CPM over $15
  * under 500 impressions after 48h (a delivery fault, not a creative one)

Baselines come from this account's own Feb-May 2026 history: $6.62 blended CPL,
$5.56 for offer-led ads, $13.17 for brand posts with no offer, 1.25% link CTR,
$10.77 CPM.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
GRAPH_ROOT = "https://graph.facebook.com"
DEFAULT_CAMPAIGN = "120250066601300337"

MIN_IMPRESSIONS_48H = 500
KILL_SPEND_NO_LEADS = 20.0
MIN_LINK_CTR = 1.0
MAX_CPM = 15.0
CTR_JUDGEMENT_IMPRESSIONS = 3000


def number(source: dict, key: str) -> float:
    try:
        return float(source.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0


def action_count(row: dict, name: str) -> float:
    for entry in row.get("actions", []) or []:
        if entry.get("action_type") == name:
            return float(entry.get("value") or 0)
    return 0.0


def fetch(graph_base: str, path: str, token: str, **params: Any) -> dict:
    params["access_token"] = token
    response = requests.get(f"{graph_base}/{path}", params=params, timeout=60)
    body = response.json()
    if "error" in body:
        raise SystemExit(f"Graph API error: {body['error'].get('message')}")
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-id", default=DEFAULT_CAMPAIGN)
    parser.add_argument("--leads", action="store_true",
                        help="Also list submitted leads (needs leads_retrieval)")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    token = os.environ.get("META_ACCESS_TOKEN")
    if not token:
        raise SystemExit("META_ACCESS_TOKEN must be set in .env")
    base = f"{GRAPH_ROOT}/{os.environ.get('META_API_VERSION', 'v24.0')}"

    campaign = fetch(base, args.campaign_id, token,
                     fields="name,status,effective_status,lifetime_budget,created_time")
    budget = number(campaign, "lifetime_budget") / 100

    print("=" * 68)
    print(campaign.get("name", args.campaign_id))
    print(f"status {campaign.get('effective_status')} | budget ${budget:.2f}")
    print("=" * 68)

    insights = fetch(
        base, f"{args.campaign_id}/insights", token,
        fields="spend,impressions,reach,frequency,clicks,inline_link_clicks,cpm,actions",
        date_preset="maximum",
    ).get("data", [])

    if not insights:
        print("\nNo delivery yet. If the campaign is ACTIVE and this persists")
        print("beyond a few hours, check billing and that the ad passed review.")
        return 0

    row = insights[0]
    spend = number(row, "spend")
    impressions = number(row, "impressions")
    reach = number(row, "reach")
    link_clicks = number(row, "inline_link_clicks")
    leads = action_count(row, "lead")
    cpm = number(row, "cpm")
    link_ctr = (link_clicks / impressions * 100) if impressions else 0.0
    cpl = (spend / leads) if leads else 0.0

    started = campaign.get("created_time", "")
    hours = 0.0
    if started:
        begin = datetime.strptime(started[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        hours = (datetime.now(timezone.utc) - begin).total_seconds() / 3600

    print(f"\n  elapsed        {hours:.0f}h")
    print(f"  spend          ${spend:.2f} of ${budget:.2f}")
    print(f"  impressions    {impressions:,.0f}   reach {reach:,.0f}")
    print(f"  link clicks    {link_clicks:,.0f}   link CTR {link_ctr:.2f}%  (target >=1.40%)")
    print(f"  CPM            ${cpm:.2f}          (target <=$12)")
    print(f"  leads          {leads:.0f}")
    print(f"  CPL            ${cpl:.2f}" if leads else "  CPL            n/a")

    print("\n  " + "-" * 64)
    verdicts: list[str] = []
    if hours >= 48 and impressions < MIN_IMPRESSIONS_48H:
        verdicts.append("KILL - delivery fault: check rejection, billing, schedule")
    if spend >= KILL_SPEND_NO_LEADS and leads == 0:
        verdicts.append(f"KILL - ${spend:.2f} spent, zero leads")
    if impressions >= CTR_JUDGEMENT_IMPRESSIONS and link_ctr < MIN_LINK_CTR:
        verdicts.append(f"KILL - link CTR {link_ctr:.2f}% under {MIN_LINK_CTR}%")
    if cpm > MAX_CPM:
        verdicts.append(f"WARN - CPM ${cpm:.2f} over ${MAX_CPM}")
    if leads and cpl > 8.0:
        verdicts.append(f"WARN - CPL ${cpl:.2f} above the $8 intervention point")
    if leads and cpl <= 6.0:
        verdicts.append(f"GOOD - CPL ${cpl:.2f} at or under the $6 target")

    if not verdicts:
        verdicts.append("HOLD - nothing has crossed a threshold yet")
    for line in verdicts:
        print(f"  {line}")
    print("  " + "-" * 64)

    if args.leads:
        forms = fetch(base, f"{args.campaign_id}/ads", token, fields="id,name").get("data", [])
        print(f"\n  {len(forms)} ad(s) in this campaign")
        print("  Pull submitted leads from the form directly:")
        print("    GET /<form_id>/leads   (form 2037712420283771)")

    return 0


if __name__ == "__main__":
    sys.exit(main())

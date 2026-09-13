"""Export the complete read-only Meta Ads history for one ad account.

Credentials are loaded from the repository's ignored ``.env`` file. The
export contains account/campaign/ad set/ad/creative metadata plus daily and
aggregate performance. It never requests leads or other customer-level data.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
GRAPH_ROOT = "https://graph.facebook.com"
DEFAULT_ACCOUNT_ID = "614367564654088"
DEFAULT_API_VERSION = "v24.0"
HOUSTON_META_CITY_ID = "2528590"

ACCOUNT_FIELDS = ",".join(
    (
        "id",
        "name",
        "account_id",
        "account_status",
        "currency",
        "timezone_name",
        "timezone_offset_hours_utc",
        "business_name",
        "amount_spent",
        "spend_cap",
        "created_time",
    )
)
CAMPAIGN_FIELDS = ",".join(
    (
        "id",
        "account_id",
        "name",
        "status",
        "effective_status",
        "objective",
        "buying_type",
        "bid_strategy",
        "daily_budget",
        "lifetime_budget",
        "budget_remaining",
        "special_ad_categories",
        "created_time",
        "updated_time",
        "start_time",
        "stop_time",
    )
)
ADSET_FIELDS = ",".join(
    (
        "id",
        "account_id",
        "campaign_id",
        "name",
        "status",
        "effective_status",
        "created_time",
        "updated_time",
        "start_time",
        "end_time",
        "daily_budget",
        "lifetime_budget",
        "bid_amount",
        "bid_strategy",
        "billing_event",
        "optimization_goal",
        "destination_type",
        "attribution_spec",
        "promoted_object",
        "targeting",
    )
)
AD_FIELDS = ",".join(
    (
        "id",
        "account_id",
        "campaign_id",
        "adset_id",
        "name",
        "status",
        "effective_status",
        "created_time",
        "updated_time",
        "tracking_specs",
        "conversion_domain",
        "creative{id,name}",
    )
)
CREATIVE_FIELDS = ",".join(
    (
        "id",
        "account_id",
        "name",
        "status",
        "title",
        "body",
        "call_to_action_type",
        "link_url",
        "url_tags",
        "thumbnail_url",
        "image_url",
        "image_hash",
        "video_id",
        "object_story_id",
        "effective_object_story_id",
        "object_story_spec",
        "asset_feed_spec",
    )
)

INSIGHT_DIMENSIONS = (
    "date_start",
    "date_stop",
    "account_id",
    "account_name",
    "campaign_id",
    "campaign_name",
    "adset_id",
    "adset_name",
    "ad_id",
    "ad_name",
    "objective",
    "optimization_goal",
    "buying_type",
)
INSIGHT_METRICS = (
    "spend",
    "impressions",
    "reach",
    "frequency",
    "cpm",
    "clicks",
    "inline_link_clicks",
    "ctr",
    "cpc",
    "cost_per_inline_link_click",
    "outbound_clicks",
    "outbound_clicks_ctr",
    "cost_per_outbound_click",
    "website_ctr",
    "actions",
    "action_values",
    "cost_per_action_type",
    "conversions",
    "conversion_values",
    "cost_per_conversion",
    "video_play_actions",
    "video_p25_watched_actions",
    "video_p50_watched_actions",
    "video_p75_watched_actions",
    "video_p95_watched_actions",
    "video_p100_watched_actions",
    "video_thruplay_watched_actions",
    "cost_per_thruplay",
)
INSIGHT_FIELDS = ",".join((*INSIGHT_DIMENSIONS, *INSIGHT_METRICS))
AD_RANKING_FIELDS = ",".join(
    (
        *INSIGHT_DIMENSIONS,
        "spend",
        "impressions",
        "reach",
        "frequency",
        "cpm",
        "clicks",
        "inline_link_clicks",
        "ctr",
        "cpc",
        "actions",
        "cost_per_action_type",
        "quality_ranking",
        "engagement_rate_ranking",
        "conversion_rate_ranking",
    )
)
ARRAY_METRICS = {
    "actions": "action",
    "action_values": "action_value",
    "cost_per_action_type": "cost_per_action",
    "conversions": "conversion",
    "conversion_values": "conversion_value",
    "cost_per_conversion": "cost_per_conversion",
    "outbound_clicks": "outbound_click",
    "outbound_clicks_ctr": "outbound_click_ctr",
    "cost_per_outbound_click": "cost_per_outbound_click",
    "website_ctr": "website_ctr",
    "video_play_actions": "video_play",
    "video_p25_watched_actions": "video_p25",
    "video_p50_watched_actions": "video_p50",
    "video_p75_watched_actions": "video_p75",
    "video_p95_watched_actions": "video_p95",
    "video_p100_watched_actions": "video_p100",
    "video_thruplay_watched_actions": "video_thruplay",
    "cost_per_thruplay": "cost_per_thruplay",
}


class MetaApiError(RuntimeError):
    pass


def normalize_account_id(value: str) -> str:
    value = value.strip().removeprefix("act_")
    if not value.isdigit():
        raise ValueError("Ad account ID must contain digits only.")
    return f"act_{value}"


class MetaClient:
    def __init__(self, token: str, api_version: str) -> None:
        self.api_version = api_version
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{GRAPH_ROOT}/{self.api_version}/{path.lstrip('/')}"
        for attempt in range(5):
            try:
                response = self.session.get(url, params=params, timeout=90)
                payload = response.json()
            except requests.RequestException as exc:
                if attempt == 4:
                    raise MetaApiError(f"Could not connect to Meta: {exc}") from exc
                time.sleep(2**attempt)
                continue
            except ValueError as exc:
                raise MetaApiError(
                    f"Meta returned non-JSON (HTTP {response.status_code})."
                ) from exc

            if response.ok and "error" not in payload:
                return payload

            error = payload.get("error", {})
            code = error.get("code")
            if code in {1, 2, 4, 17, 32, 613} and attempt < 4:
                time.sleep(2**attempt)
                continue
            message = error.get("message", f"HTTP {response.status_code}")
            subcode = error.get("error_subcode")
            raise MetaApiError(f"{message} (code={code}, subcode={subcode})")
        raise AssertionError("unreachable")

    def get_all(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page_params = dict(params)
        while True:
            payload = self.get(path, page_params)
            rows.extend(payload.get("data", []))
            after = payload.get("paging", {}).get("cursors", {}).get("after")
            if not after or not payload.get("paging", {}).get("next"):
                return rows
            page_params["after"] = after


def json_cell(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value


def flatten_insight(row: dict[str, Any]) -> dict[str, Any]:
    flat = {key: json_cell(value) for key, value in row.items() if key not in ARRAY_METRICS}
    for source, prefix in ARRAY_METRICS.items():
        for item in row.get(source, []) or []:
            action_type = str(item.get("action_type", "unknown"))
            flat[f"{prefix}__{action_type}"] = item.get("value", "")
    return flat


def adset_targets_houston(adset: dict[str, Any]) -> bool:
    """Identify Houston from Meta's geo target, independent of naming."""
    targeting = adset.get("targeting") or {}
    geo = targeting.get("geo_locations") or {}
    locations = [
        *(geo.get("places") or []),
        *(geo.get("custom_locations") or []),
        *(geo.get("cities") or []),
    ]
    for location in locations:
        if str(location.get("primary_city_id", "")) == HOUSTON_META_CITY_ID:
            return True
        name = " ".join(
            str(location.get(key, ""))
            for key in ("name", "address_string")
        ).lower()
        if "houston" in name:
            return True
        try:
            latitude = float(location.get("latitude"))
            longitude = float(location.get("longitude"))
        except (TypeError, ValueError):
            continue
        if 29.5 <= latitude <= 30.0 and -95.9 <= longitude <= -95.1:
            return True
    return False


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    materialized = [{key: json_cell(value) for key, value in row.items()} for row in rows]
    fieldnames = sorted({key for row in materialized for key in row})
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if fieldnames:
            writer.writeheader()
            writer.writerows(materialized)
    return len(materialized)


def fetch_insights(
    client: MetaClient,
    account_id: str,
    *,
    since: str,
    until: str,
    level: str,
    fields: str = INSIGHT_FIELDS,
    time_increment: int | None = None,
    breakdowns: str | None = None,
    campaign_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "fields": fields,
        "level": level,
        "time_range": json.dumps({"since": since, "until": until}),
        "limit": 500,
        "use_account_attribution_setting": "true",
        "action_report_time": "conversion",
    }
    if campaign_ids:
        params["filtering"] = json.dumps(
            [{"field": "campaign.id", "operator": "IN", "value": campaign_ids}]
        )
    if time_increment is not None:
        params["time_increment"] = time_increment
    if breakdowns:
        params["breakdowns"] = breakdowns
    return client.get_all(f"{account_id}/insights", params)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", default=os.getenv("META_AD_ACCOUNT_ID", DEFAULT_ACCOUNT_ID))
    parser.add_argument("--api-version", default=os.getenv("META_API_VERSION", DEFAULT_API_VERSION))
    parser.add_argument("--since", help="First delivery date (YYYY-MM-DD); defaults to account creation.")
    parser.add_argument(
        "--until",
        help="Last delivery date (YYYY-MM-DD); defaults to yesterday (a complete day).",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output" / "meta_ads_houston")
    return parser.parse_args()


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    args = parse_args()
    token = os.getenv("META_ACCESS_TOKEN")
    if not token:
        print("META_ACCESS_TOKEN is missing from .env.", file=sys.stderr)
        return 2

    account_id = normalize_account_id(args.account_id)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    client = MetaClient(token, args.api_version)

    print("Fetching account metadata...")
    account = client.get(account_id, {"fields": ACCOUNT_FIELDS})
    if "houston" not in str(account.get("name", "")).lower():
        raise MetaApiError(
            f"Safety check failed: account name {account.get('name')!r} does not contain 'Houston'."
        )

    print("Fetching campaigns, ad sets, ads, and creatives...")
    all_campaigns = client.get_all(
        f"{account_id}/campaigns", {"fields": CAMPAIGN_FIELDS, "limit": 500}
    )
    all_adsets = client.get_all(f"{account_id}/adsets", {"fields": ADSET_FIELDS, "limit": 500})
    all_ads = client.get_all(f"{account_id}/ads", {"fields": AD_FIELDS, "limit": 500})
    all_creatives = client.get_all(
        f"{account_id}/adcreatives", {"fields": CREATIVE_FIELDS, "limit": 500}
    )

    adsets = [row for row in all_adsets if adset_targets_houston(row)]
    campaign_ids = sorted({row["campaign_id"] for row in adsets})
    if not campaign_ids:
        raise MetaApiError("No ad sets with Houston geo targeting were found.")
    campaigns = [row for row in all_campaigns if row["id"] in campaign_ids]
    campaign_id_set = set(campaign_ids)
    ads = [row for row in all_ads if row.get("campaign_id") in campaign_id_set]
    creative_ids = {
        str(row.get("creative", {}).get("id"))
        for row in ads
        if row.get("creative", {}).get("id")
    }
    creatives = [row for row in all_creatives if row.get("id") in creative_ids]
    print(
        f"Houston geo filter retained {len(campaigns)} campaigns, {len(adsets)} ad sets, "
        f"{len(ads)} ads, and {len(creatives)} creatives."
    )

    created_date = datetime.fromisoformat(account["created_time"]).date()
    campaign_dates = [
        datetime.fromisoformat(row["created_time"]).date()
        for row in campaigns
        if row.get("created_time")
    ]
    default_since = min(campaign_dates, default=created_date)
    since = date.fromisoformat(args.since) if args.since else default_since
    until = date.fromisoformat(args.until) if args.until else date.today() - timedelta(days=1)
    if since > until:
        raise ValueError(f"since ({since}) must be on or before until ({until})")
    since_s, until_s = since.isoformat(), until.isoformat()
    print(f"Fetching performance from {since_s} through {until_s}...")

    insight_specs = {
        "insights_account_lifetime": {"level": "account"},
        "insights_campaign_lifetime": {"level": "campaign"},
        "insights_adset_lifetime": {"level": "adset"},
        "insights_ad_lifetime": {"level": "ad"},
        "insights_campaign_daily": {"level": "campaign", "time_increment": 1},
        "insights_adset_daily": {"level": "adset", "time_increment": 1},
        "insights_ad_daily": {"level": "ad", "time_increment": 1},
        "insights_campaign_demographics": {
            "level": "campaign",
            "breakdowns": "age,gender",
        },
        "insights_campaign_placement": {
            "level": "campaign",
            "breakdowns": "publisher_platform,platform_position,device_platform",
        },
        "insights_campaign_region": {"level": "campaign", "breakdowns": "region"},
    }
    insights: dict[str, list[dict[str, Any]]] = {}
    for name, spec in insight_specs.items():
        print(f"  {name}...")
        insights[name] = fetch_insights(
            client,
            account_id,
            since=since_s,
            until=until_s,
            campaign_ids=campaign_ids,
            **spec,
        )

    print("  insights_ad_rankings...")
    insights["insights_ad_rankings"] = fetch_insights(
        client,
        account_id,
        since=since_s,
        until=until_s,
        level="ad",
        fields=AD_RANKING_FIELDS,
        campaign_ids=campaign_ids,
    )

    write_json(output_dir / "account.json", account)
    counts = {
        "campaigns": write_csv(output_dir / "campaigns.csv", campaigns),
        "adsets": write_csv(output_dir / "adsets.csv", adsets),
        "ads": write_csv(output_dir / "ads.csv", ads),
        "creatives": write_csv(output_dir / "creatives.csv", creatives),
    }
    for name, rows in insights.items():
        counts[name] = write_csv(output_dir / f"{name}.csv", map(flatten_insight, rows))

    manifest = {
        "exported_at": datetime.now().astimezone().isoformat(),
        "api_version": args.api_version,
        "account_id": account_id,
        "account_name": account.get("name"),
        "currency": account.get("currency"),
        "timezone": account.get("timezone_name"),
        "date_range": {"since": since_s, "until": until_s},
        "attribution": "Account attribution setting; actions reported by conversion time.",
        "scope": "Aggregate ads delivery and creative metadata only; no lead/customer records.",
        "houston_filter": {
            "method": "Ad-set geo targeting",
            "meta_primary_city_id": HOUSTON_META_CITY_ID,
            "campaign_ids": campaign_ids,
        },
        "row_counts": counts,
    }
    write_json(output_dir / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (MetaApiError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)

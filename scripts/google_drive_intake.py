"""Read a bounded Google Drive folder into a sanitized local asset inventory."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from cricket_posts.drive_intake import (
    DriveAuthenticationError,
    DriveIntakeConfig,
    GoogleDriveClient,
    ingest_drive_folder,
)


ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", required=True, help="Google Drive folder URL or ID")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "output" / "drive_intake",
        help="Ignored local directory for downloaded assets and inventory.json",
    )
    parser.add_argument("--max-files", type=int, default=32)
    parser.add_argument("--max-videos", type=int, default=6)
    parser.add_argument("--max-video-seconds", type=float, default=180.0)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    load_dotenv(ROOT / ".env")
    token = os.getenv("GOOGLE_DRIVE_ACCESS_TOKEN", "")
    if not token:
        raise DriveAuthenticationError(
            "GOOGLE_DRIVE_ACCESS_TOKEN is missing. Complete read-only OAuth and keep the token in .env."
        )
    config = DriveIntakeConfig(
        max_files=args.max_files,
        max_videos=args.max_videos,
        max_video_duration_seconds=args.max_video_seconds,
    )
    receipt = ingest_drive_folder(
        GoogleDriveClient(token),
        args.folder,
        args.output / "assets",
        config=config,
    )
    receipt_path = receipt.write(args.output / "inventory.json")
    imported = len(receipt.imported)
    quarantined = sum(asset.status.value == "quarantined" for asset in receipt.assets)
    skipped = sum(asset.status.value == "skipped" for asset in receipt.assets)
    print("Google Drive read-only intake complete")
    print(f"Folder ref : {receipt.folder_ref}")
    print(f"Imported   : {imported}")
    print(f"Quarantined: {quarantined}")
    print(f"Skipped    : {skipped}")
    print(f"Receipt    : {receipt_path}")
    for question in receipt.questions:
        print(f"Needs input: {question}")


if __name__ == "__main__":
    main()


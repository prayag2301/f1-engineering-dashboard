#!/usr/bin/env python3
"""
Fetch upgrade reports from RSS feeds and ingest mapped entries into the database.

Examples:
  python backend/scripts/fetch_upgrades.py --season 2025 --max-entries 40
  python backend/scripts/fetch_upgrades.py --dry-run
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Make "backend" importable regardless of where this script is launched from.
API_ROOT = Path(__file__).resolve().parents[2]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from backend.database import SessionLocal
from backend.ingestion import ingest_upgrade_items
from backend.services.upgrade_tracker import collect_upgrade_ingest_items


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch and ingest F1 upgrade reports")
    parser.add_argument("--season", type=int, default=None, help="Optional race season filter")
    parser.add_argument(
        "--max-entries",
        type=int,
        default=50,
        help="Maximum number of mapped entries to ingest (default: 50)",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Do not run intelligence enrichment on missing fields",
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Do not skip duplicate upgrade records",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print mapping stats and sample payloads",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    db = SessionLocal()

    try:
        items, stats = collect_upgrade_ingest_items(
            db=db,
            season=args.season,
            max_entries=args.max_entries,
        )

        print(
            json.dumps(
                {
                    "scanned_entries": stats.scanned_entries,
                    "candidates": stats.candidates,
                    "skipped_non_upgrade": stats.skipped_non_upgrade,
                    "skipped_no_team": stats.skipped_no_team,
                    "skipped_no_component": stats.skipped_no_component,
                    "skipped_no_race": stats.skipped_no_race,
                    "feed_errors": stats.feed_errors,
                },
                indent=2,
            )
        )

        if args.dry_run:
            preview = [item.model_dump() for item in items[:5]]
            print("\nDry-run preview (first 5 mapped entries):")
            print(json.dumps(preview, indent=2, default=str))
            return 0

        if not items:
            print("\nNo mappable entries found.")
            return 0

        outcome = ingest_upgrade_items(
            db=db,
            items=items,
            enrich_missing_fields=not args.no_enrich,
            skip_duplicates=not args.no_dedupe,
        )
        db.commit()

        print(
            json.dumps(
                {
                    "created": len(outcome.created),
                    "skipped_duplicates": outcome.skipped_duplicates,
                    "upgrade_ids": [str(upgrade.id) for upgrade in outcome.created],
                },
                indent=2,
            )
        )
        return 0

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())

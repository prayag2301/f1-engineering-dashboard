#!/usr/bin/env python3
"""Collect a portable weekly reference report without a database or credentials.

Run with the backend environment. Published geometry is never changed by intake.
The report can be imported into the local review inbox with `app.cli import-weekly`.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.sources import (
    fetch_bytes,
    parse_document,
    canonical_url,
    TEAM_PATTERNS,
    discover_links,
)


def collect(config, *, days=14, previous=None, moment=None):
    moment = moment or datetime.now(timezone.utc)
    cutoff = moment - timedelta(days=days)
    known = {
        item["url"]: item["fingerprint"]
        for item in (previous or {}).get("documents", [])
    }
    documents, errors, sources, seen = [], [], [], set()
    for entry in config["sources"]:
        stats = {
            "url": entry["url"],
            "team_key": entry.get("team_key"),
            "discovered": 0,
            "checked": 0,
            "status": "ok",
        }
        try:
            data, mime, final = fetch_bytes(entry["url"])
            links = discover_links(entry, data, final)
            if not links:
                stats["status"] = "partial"
                errors.append(
                    {
                        "url": entry["url"],
                        "error": "No readable matching article links; source coverage is incomplete.",
                    }
                )
            stats["discovered"] = len(links)
            for item in links[: entry.get("limit", 5)]:
                url = canonical_url(item["url"])
                if url in seen:
                    continue
                seen.add(url)
                try:
                    content, kind, url = fetch_bytes(url)
                    parsed = parse_document(content, kind, url)
                    stats["checked"] += 1
                    date = parsed["published_at"] or item.get("published_at")
                    if date and date.tzinfo is None:
                        date = date.replace(tzinfo=timezone.utc)
                    if date and (date < cutoff or date > moment):
                        continue
                    teams = [
                        team
                        for team, pattern in TEAM_PATTERNS.items()
                        if re.search(
                            pattern, parsed["title"] + "\n" + parsed["text"], re.I
                        )
                    ]
                    if not teams and entry.get("team_key"):
                        teams = [entry["team_key"]]
                    normalized = re.sub(r"\s+", " ", parsed["text"]).strip()
                    fingerprint = hashlib.sha256(
                        json.dumps(
                            [normalized, parsed["image_urls"]], sort_keys=True
                        ).encode()
                    ).hexdigest()
                    documents.append(
                        {
                            "url": canonical_url(url),
                            "title": parsed["title"],
                            "published_at": date.isoformat() if date else None,
                            "retrieved_at": moment.isoformat(),
                            "date_status": (
                                "dated" if date else "unknown — review required"
                            ),
                            "teams": teams,
                            "image_urls": parsed["image_urls"],
                            "fingerprint": fingerprint,
                            "changed": known.get(canonical_url(url)) != fingerprint,
                        }
                    )
                except Exception as error:
                    errors.append({"url": url, "error": str(error)[:500]})
                    stats["status"] = "partial"
        except Exception as error:
            errors.append({"url": entry["url"], "error": str(error)[:500]})
            stats["status"] = "failed"
        sources.append(stats)
    successful = sum(s["checked"] for s in sources)
    return {
        "schema_version": 1,
        "generated_at": moment.isoformat(),
        "window_days": days,
        "coverage": "failed" if not successful else "partial" if errors else "complete",
        "documents": documents,
        "sources": sources,
        "errors": errors,
        "publication": "Reference discovery only. New photos do not establish a modeled upgrade.",
    }


def markdown(report):
    lines = [
        "# Weekly F1 reference intake",
        "",
        f"Checked: {report['generated_at']} · Coverage: {report['coverage']}",
        "",
        report["publication"],
        "",
    ]
    for team in TEAM_PATTERNS:
        docs = [d for d in report["documents"] if team in d["teams"] and d["changed"]]
        lines.extend([f'## {team.replace("_", " ").title()}', ""])
        lines.extend(
            [
                f"- [{d['title'].replace('[', '').replace(']', '')}]({d['url']}) — {d['published_at'] or 'date unknown'}; {len(d['image_urls'])} image references"
                for d in docs
            ]
            or ["No new dated evidence established in the checked sources."]
        )
        lines.append("")
    if report["errors"]:
        lines.extend(["## Collection failures", ""])
        lines.extend(f"- {e['url']}: {e['error']}" for e in report["errors"])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()
    if not 1 <= args.days <= 90:
        parser.error("--days must be between 1 and 90")
    if args.output.exists():
        parser.error("Choose a new output directory to preserve previous reports")
    previous = json.loads(args.previous.read_text()) if args.previous else None
    report = collect(
        json.loads((ROOT / "data/references/sources.json").read_text()),
        days=args.days,
        previous=previous,
    )
    args.output.mkdir(parents=True)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "report.md").write_text(markdown(report))
    print(
        f"{report['coverage']}: {len(report['documents'])} references, {len(report['errors'])} errors. {args.output}"
    )
    return 1 if report["coverage"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())

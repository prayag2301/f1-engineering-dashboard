#!/usr/bin/env python3
"""
seed_regulations.py
-------------------
Parses the FIA F1 Technical Regulations PDF (if present) and seeds the
regulation_constraints table in the database.

Usage:
    # With a PDF (recommended):
    python -m scripts.seed_regulations --pdf data/regulations/fia_2026_tech_regs.pdf

    # Without a PDF — uses curated static dataset:
    python -m scripts.seed_regulations

    # Force re-seed (drops and replaces existing records for the season):
    python -m scripts.seed_regulations --force
"""

import argparse
import sys
from pathlib import Path

# Ensure backend/app package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, engine, Base
from app.models.models import RegulationConstraint
from app.services.regulation_parser import parse_regulations


def find_default_pdf() -> str | None:
    repo_root = Path(__file__).resolve().parents[2]
    regulations_dir = repo_root / "data" / "regulations"
    if not regulations_dir.exists():
        return None
    pdf_files = sorted(regulations_dir.glob("*.pdf"))
    return str(pdf_files[-1]) if pdf_files else None


def seed(pdf_path: str | None = None, season: int = 2026, force: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    pdf_to_use = pdf_path or find_default_pdf()

    db = SessionLocal()
    try:
        existing = (
            db.query(RegulationConstraint)
            .filter(RegulationConstraint.season == season)
            .count()
        )

        if existing > 0 and not force:
            print(
                f"Regulations for season {season} already seeded ({existing} records). "
                "Pass --force to replace."
            )
            return

        if existing > 0 and force:
            print(f"Removing {existing} existing constraints for season {season}…")
            db.query(RegulationConstraint).filter(
                RegulationConstraint.season == season
            ).delete()
            db.commit()

        constraints = parse_regulations(pdf_path=pdf_to_use, season=season)
        source_label = f"PDF ({pdf_to_use})" if pdf_to_use else "static fallback"
        print(f"Parsed {len(constraints)} constraints (source: {source_label}).")

        for c in constraints:
            obj = RegulationConstraint(
                season=c.season,
                component=c.component,
                parameter=c.parameter,
                value=c.value,
                unit=c.unit,
                article_ref=c.article_ref,
                notes=c.notes,
            )
            db.add(obj)

        db.commit()
        print(f"Seeded {len(constraints)} regulation constraints for season {season}.")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed FIA regulation constraints into the database")
    parser.add_argument("--pdf", type=str, default=None, help="Path to FIA technical regulations PDF")
    parser.add_argument("--season", type=int, default=2026, help="Season year (default: 2026)")
    parser.add_argument("--force", action="store_true", help="Replace existing records for the season")
    args = parser.parse_args()

    seed(pdf_path=args.pdf, season=args.season, force=args.force)

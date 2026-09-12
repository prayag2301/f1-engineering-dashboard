"""Reviewed regulation registry. Free-text extraction does not establish a rule."""

from dataclasses import dataclass
import json
from pathlib import Path
from app.config import get_settings


@dataclass
class ParsedConstraint:
    season: int
    component: str
    parameter: str
    value: float
    unit: str
    article_ref: str
    notes: str | None = None


def get_static_constraints(season: int = 2026):
    if season != 2026:
        raise ValueError("No reviewed regulation set for this season.")
    document = json.loads(
        (get_settings().REFERENCE_ROOT / "regulations-2026.json").read_text()
    )
    return [
        ParsedConstraint(
            season=season,
            **{k: v for k, v in rule.items() if k != "page"},
        )
        for rule in document["constraints"]
    ]


def parse_regulations(pdf_path: str | Path | None = None, season: int = 2026):
    if pdf_path is not None:
        raise ValueError(
            "Import new PDFs as source documents and review the constraints before changing the registry."
        )
    return get_static_constraints(season)

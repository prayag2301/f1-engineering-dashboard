"""
Extract dimensional constraints from FIA F1 technical regulations PDFs.

Week 4 scope (v1):
- front wing
- rear wing
- floor / diffuser
- overall car dimensions
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ParsedConstraint:
    season: int
    component: str
    parameter: str
    value: float
    unit: str
    article_ref: str
    notes: Optional[str] = None


TARGET_COMPONENTS = {"front_wing", "rear_wing", "floor", "diffuser", "overall"}

STATIC_CONSTRAINTS_2026: list[dict] = [
    {"component": "overall", "parameter": "max_length", "value": 5700.0, "unit": "mm", "article_ref": "Art. 2.1", "notes": "Maximum overall car length"},
    {"component": "overall", "parameter": "max_width", "value": 2000.0, "unit": "mm", "article_ref": "Art. 2.2", "notes": "Maximum overall car width"},
    {"component": "overall", "parameter": "max_height", "value": 1000.0, "unit": "mm", "article_ref": "Art. 2.3", "notes": "Maximum overall car height"},
    {"component": "overall", "parameter": "min_weight", "value": 800.0, "unit": "kg", "article_ref": "Art. 4.1", "notes": "Minimum car + driver weight"},
    {"component": "front_wing", "parameter": "max_width", "value": 1800.0, "unit": "mm", "article_ref": "Art. 3.9.1", "notes": "Maximum front wing width"},
    {"component": "front_wing", "parameter": "max_forward_overhang", "value": 1000.0, "unit": "mm", "article_ref": "Art. 3.9.2", "notes": "Maximum front overhang"},
    {"component": "front_wing", "parameter": "max_height_above_ref", "value": 400.0, "unit": "mm", "article_ref": "Art. 3.9.3", "notes": "Maximum front wing height"},
    {"component": "front_wing", "parameter": "max_camber_angle", "value": 25.0, "unit": "deg", "article_ref": "Art. 3.9.5", "notes": "Maximum front wing angle"},
    {"component": "rear_wing", "parameter": "max_width", "value": 1050.0, "unit": "mm", "article_ref": "Art. 3.10.1", "notes": "Maximum rear wing width"},
    {"component": "rear_wing", "parameter": "max_height_above_ref", "value": 950.0, "unit": "mm", "article_ref": "Art. 3.10.2", "notes": "Maximum rear wing height"},
    {"component": "rear_wing", "parameter": "min_height_above_ref", "value": 750.0, "unit": "mm", "article_ref": "Art. 3.10.3", "notes": "Minimum rear wing lower element height"},
    {"component": "rear_wing", "parameter": "max_chord_mainplane", "value": 500.0, "unit": "mm", "article_ref": "Art. 3.10.4", "notes": "Maximum rear wing chord"},
    {"component": "rear_wing", "parameter": "drs_max_open_angle", "value": 85.0, "unit": "deg", "article_ref": "Art. 3.10.5", "notes": "Maximum DRS-open flap angle"},
    {"component": "floor", "parameter": "max_width", "value": 1600.0, "unit": "mm", "article_ref": "Art. 3.11.1", "notes": "Maximum floor width"},
    {"component": "floor", "parameter": "leading_edge_max_height", "value": 100.0, "unit": "mm", "article_ref": "Art. 3.11.2", "notes": "Maximum floor leading-edge height"},
    {"component": "floor", "parameter": "min_thickness", "value": 10.0, "unit": "mm", "article_ref": "Art. 3.11.5", "notes": "Minimum floor thickness"},
    {"component": "diffuser", "parameter": "max_width", "value": 1050.0, "unit": "mm", "article_ref": "Art. 3.12.1", "notes": "Maximum diffuser width"},
    {"component": "diffuser", "parameter": "max_height_exit", "value": 350.0, "unit": "mm", "article_ref": "Art. 3.12.2", "notes": "Maximum diffuser exit height"},
    {"component": "diffuser", "parameter": "max_expansion_half_angle", "value": 15.0, "unit": "deg", "article_ref": "Art. 3.12.3", "notes": "Maximum diffuser expansion half-angle"},
]

_VALUE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mm(?:\u00b2)?|mm2|kg|deg|°)", re.IGNORECASE)
_ARTICLE_RE = re.compile(r"(?:Art(?:icle)?\.?\s*)?(\d+\.\d+(?:\.\d+)?)", re.IGNORECASE)

_COMPONENT_KEYWORDS: dict[str, list[str]] = {
    "front_wing": ["front wing", "front aerofoil"],
    "rear_wing": ["rear wing", "rear aerofoil", "drs"],
    "floor": ["floor", "underfloor", "ground effect"],
    "diffuser": ["diffuser", "diffusor"],
    "overall": ["overall", "car dimensions", "maximum overall", "minimum weight"],
}

_NON_TARGET_COMPONENT_KEYWORDS = ("sidepod", "side pod", "nose cone", "nose tip", "beam wing", "brake duct")

_DIMENSIONAL_KEYWORDS = {
    "width",
    "height",
    "length",
    "chord",
    "angle",
    "radius",
    "clearance",
    "weight",
    "thickness",
    "overhang",
    "leading edge",
    "exit",
    "expansion",
}

_PARAMETER_KEYWORDS: dict[str, str] = {
    "maximum overall length": "max_length",
    "maximum overall width": "max_width",
    "maximum overall height": "max_height",
    "minimum weight": "min_weight",
    "maximum width": "max_width",
    "minimum width": "min_width",
    "maximum height": "max_height_above_ref",
    "minimum height": "min_height_above_ref",
    "maximum chord": "max_chord_mainplane",
    "maximum angle": "max_camber_angle",
    "drs": "drs_max_open_angle",
    "overhang": "max_forward_overhang",
    "leading edge": "leading_edge_max_height",
    "minimum thickness": "min_thickness",
    "exit height": "max_height_exit",
    "expansion": "max_expansion_half_angle",
}


def _normalise_unit(raw: str) -> str:
    unit = raw.strip().lower()
    if unit in {"°", "deg"}:
        return "deg"
    if unit in {"mm²", "mm2"}:
        return "mm2"
    return unit


def _extract_article_ref(text: str) -> str:
    match = _ARTICLE_RE.search(text)
    return f"Art. {match.group(1)}" if match else ""


def _extract_article_number(text: str) -> str | None:
    match = _ARTICLE_RE.search(text)
    return match.group(1) if match else None


def _component_from_article(article_number: str) -> str | None:
    if article_number.startswith("3.9"):
        return "front_wing"
    if article_number.startswith("3.10"):
        return "rear_wing"
    if article_number.startswith("3.11"):
        return "floor"
    if article_number.startswith("3.12"):
        return "diffuser"
    if article_number.startswith("2.") or article_number.startswith("4.1"):
        return "overall"
    return None


def _classify_component(text: str) -> str | None:
    lower = text.lower()
    for component, keywords in _COMPONENT_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            return component
    return None


def _looks_dimensional(text: str, unit: str) -> bool:
    lower = text.lower()
    if unit not in {"mm", "mm2", "deg", "kg"}:
        return False
    if not any(key in lower for key in _DIMENSIONAL_KEYWORDS):
        return False
    if any(
        phrase in lower
        for phrase in ("maximum", "minimum", "shall", "must not exceed", "not exceed", "at least")
    ):
        return True
    return unit == "kg" and "weight" in lower


def _classify_parameter(text: str, unit: str) -> str | None:
    lower = text.lower()
    for keyword, parameter in _PARAMETER_KEYWORDS.items():
        if keyword in lower:
            return parameter

    if unit == "kg":
        return "min_weight"

    return None


def parse_pdf(pdf_path: str | Path, season: int = 2026) -> list[ParsedConstraint]:
    try:
        import fitz  # type: ignore[import]
    except ImportError:
        return []

    path = Path(pdf_path)
    if not path.exists():
        return []

    try:
        doc = fitz.open(str(path))
    except Exception:
        return []

    constraints: list[ParsedConstraint] = []
    dedupe_keys: set[tuple[str, str, str]] = set()
    current_article = ""
    current_component: str | None = None

    for page in doc:
        text = page.get_text("text")
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if any(keyword in line.lower() for keyword in _NON_TARGET_COMPONENT_KEYWORDS):
                continue

            article_number = _extract_article_number(line)
            if article_number:
                current_article = f"Art. {article_number}"
                current_component = _component_from_article(article_number)

            if current_component not in TARGET_COMPONENTS or not current_article:
                continue

            for match in _VALUE_RE.finditer(line):
                value = float(match.group(1))
                unit = _normalise_unit(match.group(2))
                if not _looks_dimensional(line, unit):
                    continue

                parameter = _classify_parameter(line, unit)
                if not parameter:
                    continue

                dedupe_key = (current_component, parameter, current_article)
                if dedupe_key in dedupe_keys:
                    continue
                dedupe_keys.add(dedupe_key)

                constraints.append(
                    ParsedConstraint(
                        season=season,
                        component=current_component,
                        parameter=parameter,
                        value=value,
                        unit=unit,
                        article_ref=current_article,
                        notes=line[:220],
                    )
                )

    doc.close()
    return constraints


def get_static_constraints(season: int = 2026) -> list[ParsedConstraint]:
    return [
        ParsedConstraint(
            season=season,
            component=row["component"],
            parameter=row["parameter"],
            value=row["value"],
            unit=row["unit"],
            article_ref=row["article_ref"],
            notes=row.get("notes"),
        )
        for row in STATIC_CONSTRAINTS_2026
    ]


def parse_regulations(pdf_path: str | Path | None = None, season: int = 2026) -> list[ParsedConstraint]:
    if pdf_path:
        parsed = parse_pdf(pdf_path=pdf_path, season=season)
        if len(parsed) >= 8:
            return parsed
    return get_static_constraints(season=season)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Parse FIA F1 technical regulations into structured constraints.")
    parser.add_argument("--pdf", type=str, default=None, help="Path to FIA regulations PDF")
    parser.add_argument("--season", type=int, default=2026, help="Season year")
    parser.add_argument("--json", action="store_true", help="Print output as JSON")
    args = parser.parse_args()

    rows = parse_regulations(pdf_path=args.pdf, season=args.season)
    if args.json:
        print(json.dumps([row.__dict__ for row in rows], indent=2))
    else:
        print(f"Parsed {len(rows)} constraints for season {args.season}")
        for row in rows:
            print(f"[{row.article_ref}] {row.component}.{row.parameter} = {row.value} {row.unit}")

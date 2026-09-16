from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.models.enums import ComponentZone, UpgradeCategory


@dataclass
class UpgradeIntelligenceResult:
    category: UpgradeCategory
    component_zone: ComponentZone
    confidence: float
    aero_reasoning: str
    mechanical_reasoning: str
    performance_hypothesis: str
    signals: list[str]


CATEGORY_KEYWORDS: dict[UpgradeCategory, tuple[str, ...]] = {
    UpgradeCategory.AERO: (
        "aero",
        "downforce",
        "drag",
        "wake",
        "vortex",
        "outwash",
        "flow",
        "pressure",
        "diffuser",
        "wing",
    ),
    UpgradeCategory.MECHANICAL: (
        "compliance",
        "stiffness",
        "load",
        "suspension",
        "kinematic",
        "geometry",
        "structural",
        "fatigue",
        "damper",
        "heave",
    ),
    UpgradeCategory.COOLING: (
        "cooling",
        "radiator",
        "heat",
        "thermal",
        "temperature",
        "duct",
        "inlet",
        "outlet",
        "louvre",
    ),
    UpgradeCategory.FLOOR: (
        "floor",
        "floor edge",
        "fence",
        "tunnel",
        "ground effect",
        "seal",
        "porpoising",
        "underfloor",
    ),
    UpgradeCategory.SUSPENSION: (
        "pushrod",
        "pullrod",
        "wishbone",
        "upright",
        "suspension arm",
        "anti-dive",
        "anti-squat",
    ),
    UpgradeCategory.POWER_UNIT: (
        "power unit",
        "pu",
        "ers",
        "ice",
        "turbo",
        "mguk",
        "mguh",
        "energy store",
        "combustion",
    ),
}

ZONE_KEYWORDS: dict[ComponentZone, tuple[str, ...]] = {
    ComponentZone.FRONT_WING: ("front wing", "endplate", "mainplane", "flap", "nose"),
    ComponentZone.REAR_WING: ("rear wing", "beam wing", "drs", "gurney"),
    ComponentZone.FLOOR_EDGE: ("floor edge", "edge wing", "edge profile"),
    ComponentZone.FLOOR: ("floor", "underfloor", "fence", "tunnel"),
    ComponentZone.DIFFUSER: ("diffuser", "strake", "expansion"),
    ComponentZone.SIDEPOD: ("sidepod", "coke bottle", "inlet", "cooling inlet"),
    ComponentZone.BRAKE_DUCT: ("brake duct", "duct inlet", "brake cooling"),
    ComponentZone.ENGINE_COVER: ("engine cover", "bodywork", "cooling exit", "chimney"),
    ComponentZone.SUSPENSION_ARM: ("suspension fairing", "wishbone", "suspension arm", "pushrod", "pullrod"),
    ComponentZone.HALO: ("halo",),
    ComponentZone.NOSE: ("nose", "nosecone"),
}


def _normalize_text(*parts: str | None) -> str:
    return " ".join(part.strip().lower() for part in parts if part and part.strip())


def _score_keywords(text: str, keywords: Iterable[str]) -> int:
    return sum(1 for kw in keywords if kw in text)


def infer_category(text: str) -> tuple[UpgradeCategory, list[str]]:
    best_category = UpgradeCategory.OTHER
    best_score = 0
    signals: list[str] = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = _score_keywords(text, keywords)
        if score > best_score:
            best_category = category
            best_score = score
            signals = [kw for kw in keywords if kw in text][:6]

    if best_score == 0:
        fallback_signals = []
        if "floor" in text or "underfloor" in text:
            return UpgradeCategory.FLOOR, ["fallback:floor"]
        if "suspension" in text:
            return UpgradeCategory.SUSPENSION, ["fallback:suspension"]
        if "cool" in text or "radiator" in text:
            return UpgradeCategory.COOLING, ["fallback:cooling"]
        return UpgradeCategory.AERO, fallback_signals

    return best_category, signals


def infer_component_zone(text: str) -> tuple[ComponentZone, list[str]]:
    best_zone = ComponentZone.OTHER
    best_score = 0
    signals: list[str] = []

    for zone, keywords in ZONE_KEYWORDS.items():
        score = _score_keywords(text, keywords)
        if score > best_score:
            best_zone = zone
            best_score = score
            signals = [kw for kw in keywords if kw in text][:6]

    if best_score == 0:
        return ComponentZone.OTHER, []
    return best_zone, signals


def _build_aero_reasoning(zone: ComponentZone, text: str) -> str:
    if any(term in text for term in ("vortex", "outwash", "wake")):
        return (
            f"The change targets local flow structures around the {zone.value.lower()}, "
            "with an emphasis on stabilizing vortex/wake behavior to improve downstream airflow quality."
        )
    if any(term in text for term in ("drag", "frontal area", "separation")):
        return (
            f"The update likely reduces losses around the {zone.value.lower()} by improving pressure recovery "
            "and delaying separation, trading peak load for cleaner aero efficiency."
        )
    return (
        f"The geometry revision on the {zone.value.lower()} is expected to alter pressure distribution and "
        "flow conditioning, improving consistency of aerodynamic load across ride-height/yaw changes."
    )


def _build_mechanical_reasoning(category: UpgradeCategory, text: str) -> str:
    if category in {UpgradeCategory.MECHANICAL, UpgradeCategory.SUSPENSION} or "suspension" in text:
        return (
            "Mechanical intent is likely to improve load-path stability and platform control, "
            "which can preserve aerodynamic operating windows through corner entry/exit and kerb events."
        )
    if category == UpgradeCategory.COOLING:
        return (
            "Mechanical implication is thermal margin management: maintaining stable temperatures protects "
            "power-unit reliability and allows repeatable deployment without heat-soak penalties."
        )
    return (
        "Mechanical effect is secondary but relevant: better flow consistency can reduce transient balance swings, "
        "limiting peak tire slip and helping the chassis remain in a predictable operating range."
    )


def _build_performance_hypothesis(category: UpgradeCategory, zone: ComponentZone, text: str) -> str:
    if any(term in text for term in ("top speed", "drag", "straight")) or category == UpgradeCategory.COOLING:
        return (
            "Hypothesis: net gain should appear first in straight-line efficiency and high-speed sections, "
            "with the largest benefit at power-sensitive circuits."
        )
    if zone in {ComponentZone.FLOOR, ComponentZone.FLOOR_EDGE, ComponentZone.DIFFUSER}:
        return (
            "Hypothesis: lap-time gain should concentrate in medium/high-speed corners via more stable rear load "
            "and improved consistency over a stint as floor performance remains in-window."
        )
    if zone in {ComponentZone.FRONT_WING, ComponentZone.NOSE}:
        return (
            "Hypothesis: the primary improvement should be front-end response in turn-in and mid-corner balance, "
            "with potential tire management benefits from reduced slip angle demand."
        )
    return (
        "Hypothesis: performance impact should be circuit-dependent, with measurable gains where this component "
        "dominates flow quality or balance sensitivity."
    )


def _confidence_score(text: str, category_signals: list[str], zone_signals: list[str]) -> float:
    score = 0.42
    score += min(len(text) / 500.0, 0.18)
    score += min(len(category_signals) * 0.07, 0.21)
    score += min(len(zone_signals) * 0.06, 0.18)
    if any(token in text for token in ("cfd", "%", "mm", "km/h", "lap time", "delta")):
        score += 0.06
    return round(min(score, 0.95), 2)


def analyze_upgrade(
    description: str,
    technical_detail: str | None = None,
    expected_effect: str | None = None,
    source: str | None = None,
) -> UpgradeIntelligenceResult:
    text = _normalize_text(description, technical_detail, expected_effect, source)
    category, category_signals = infer_category(text)
    zone, zone_signals = infer_component_zone(text)
    signals = list(dict.fromkeys(category_signals + zone_signals))

    return UpgradeIntelligenceResult(
        category=category,
        component_zone=zone,
        confidence=_confidence_score(text, category_signals, zone_signals),
        aero_reasoning=_build_aero_reasoning(zone, text),
        mechanical_reasoning=_build_mechanical_reasoning(category, text),
        performance_hypothesis=_build_performance_hypothesis(category, zone, text),
        signals=signals,
    )

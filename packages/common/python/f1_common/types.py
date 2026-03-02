"""Shared data types used across Python services."""

from dataclasses import dataclass, field

from f1_common.enums import UpgradeCategory, ComponentZone


@dataclass
class UpgradeIntelligenceResult:
    """Result of the upgrade intelligence analysis."""

    category: UpgradeCategory
    component_zone: ComponentZone
    confidence: float
    aero_reasoning: str
    mechanical_reasoning: str
    performance_hypothesis: str
    signals: list[str] = field(default_factory=list)


@dataclass
class EvidenceRecord:
    """An evidence item linked to an upgrade."""

    source: str
    license: str = "unknown"
    credibility_score: float = 0.5
    media_path: str | None = None
    article_path: str | None = None


@dataclass
class CalloutRecord:
    """A callout annotation on a 3D model or image."""

    label: str
    anchor_type: str = "symbolic"
    anchor_ref: str = ""
    description: str = ""

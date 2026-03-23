"""Unit tests for the upgrade intelligence engine (no database required)."""
import pytest

from backend.models.enums import ComponentZone, UpgradeCategory
from backend.upgrade_parser.intelligence import (
    _confidence_score,
    analyze_upgrade,
    infer_category,
    infer_component_zone,
)


# ── infer_category ────────────────────────────────────────────────────────────

class TestInferCategory:
    def test_aero_keywords(self):
        category, signals = infer_category("new front wing with improved downforce and outwash vortex")
        assert category == UpgradeCategory.AERO
        assert len(signals) > 0

    def test_floor_keywords(self):
        category, _ = infer_category("revised floor tunnel geometry to improve ground effect seal")
        assert category == UpgradeCategory.FLOOR

    def test_cooling_keywords(self):
        category, _ = infer_category("sidepod radiator inlet ducting for improved thermal management")
        assert category == UpgradeCategory.COOLING

    def test_mechanical_keywords(self):
        category, _ = infer_category("revised suspension geometry to improve compliance and load paths")
        assert category == UpgradeCategory.MECHANICAL

    def test_suspension_keywords(self):
        category, _ = infer_category("new pushrod and wishbone geometry targeting anti-dive behaviour")
        assert category == UpgradeCategory.SUSPENSION

    def test_power_unit_keywords(self):
        category, _ = infer_category("updated turbo specification with new mguk energy store deployment map")
        assert category == UpgradeCategory.POWER_UNIT

    def test_fallback_floor(self):
        category, _ = infer_category("underfloor revision for better sealing performance")
        assert category == UpgradeCategory.FLOOR

    def test_fallback_cooling(self):
        category, _ = infer_category("cool air routing through redesigned radiator passages")
        assert category == UpgradeCategory.COOLING

    def test_fallback_suspension(self):
        # "suspension" is a MECHANICAL keyword; SUSPENSION category requires pushrod/wishbone etc.
        category, _ = infer_category("new pushrod and wishbone anti-dive geometry")
        assert category == UpgradeCategory.SUSPENSION

    def test_no_keywords_defaults_to_aero(self):
        category, signals = infer_category("completely redesigned xyz component")
        assert category == UpgradeCategory.AERO
        assert signals == []

    def test_returns_signals_list(self):
        _, signals = infer_category("revised diffuser and floor edge for improved downforce and flow")
        assert isinstance(signals, list)

    def test_signals_capped_at_six(self):
        _, signals = infer_category(
            "aero downforce drag wake vortex outwash flow pressure diffuser wing"
        )
        assert len(signals) <= 6


# ── infer_component_zone ──────────────────────────────────────────────────────

class TestInferComponentZone:
    def test_front_wing(self):
        zone, _ = infer_component_zone("front wing endplate revision improves outwash")
        assert zone == ComponentZone.FRONT_WING

    def test_rear_wing(self):
        zone, _ = infer_component_zone("rear wing drs actuation redesign for lower drag")
        assert zone == ComponentZone.REAR_WING

    def test_diffuser(self):
        zone, _ = infer_component_zone("diffuser strake geometry revised for better expansion")
        assert zone == ComponentZone.DIFFUSER

    def test_floor(self):
        zone, _ = infer_component_zone("floor tunnel and fence profile updated")
        assert zone == ComponentZone.FLOOR

    def test_floor_edge(self):
        zone, _ = infer_component_zone("floor edge profile changes to manage outwash")
        assert zone == ComponentZone.FLOOR_EDGE

    def test_sidepod(self):
        zone, _ = infer_component_zone("sidepod coke bottle shape redesigned for cooling inlet efficiency")
        assert zone == ComponentZone.SIDEPOD

    def test_brake_duct(self):
        zone, _ = infer_component_zone("brake duct inlet updated for better brake cooling")
        assert zone == ComponentZone.BRAKE_DUCT

    def test_nose(self):
        zone, _ = infer_component_zone("nosecone tip geometry revised")
        assert zone == ComponentZone.NOSE

    def test_suspension_arm(self):
        zone, _ = infer_component_zone("wishbone suspension fairing shape updated")
        assert zone == ComponentZone.SUSPENSION_ARM

    def test_no_match_returns_other(self):
        zone, signals = infer_component_zone("something completely generic with no zone keywords")
        assert zone == ComponentZone.OTHER
        assert signals == []

    def test_returns_signals_list(self):
        _, signals = infer_component_zone("front wing endplate and flap")
        assert isinstance(signals, list)
        assert len(signals) > 0


# ── _confidence_score ─────────────────────────────────────────────────────────

class TestConfidenceScore:
    def test_score_within_bounds(self):
        score = _confidence_score("some text", ["aero", "flow"], ["front wing", "endplate"])
        assert 0.0 <= score <= 0.95

    def test_score_never_exceeds_cap(self):
        long_text = "a " * 300 + " cfd % mm km/h lap time delta"
        score = _confidence_score(
            long_text,
            ["aero", "downforce", "drag", "wake", "vortex", "outwash"],
            ["front wing", "endplate", "mainplane", "flap", "nose"],
        )
        assert score <= 0.95

    def test_more_signals_higher_score(self):
        low = _confidence_score("short text", [], [])
        high = _confidence_score(
            "longer technical description with cfd and % deltas and mm measurements",
            ["aero", "downforce", "flow"],
            ["front wing", "endplate"],
        )
        assert high > low

    def test_quantitative_tokens_boost_score(self):
        without = _confidence_score("revised floor edge geometry", ["floor"], [])
        with_tokens = _confidence_score("revised floor edge geometry cfd % mm lap time delta", ["floor"], [])
        assert with_tokens > without

    def test_score_is_rounded_to_two_decimals(self):
        score = _confidence_score("text", ["aero"], ["front wing"])
        assert score == round(score, 2)


# ── analyze_upgrade ───────────────────────────────────────────────────────────

class TestAnalyzeUpgrade:
    def test_returns_full_result(self):
        result = analyze_upgrade(
            description="revised front wing endplate to improve outwash vortex",
            technical_detail="cfd-optimised profile reducing induced drag by 2%",
            expected_effect="improved front-end balance in high-speed corners",
        )
        assert result.category == UpgradeCategory.AERO
        assert result.component_zone == ComponentZone.FRONT_WING
        assert 0.0 < result.confidence <= 0.95
        assert result.aero_reasoning
        assert result.mechanical_reasoning
        assert result.performance_hypothesis
        assert isinstance(result.signals, list)

    def test_minimal_description_still_works(self):
        result = analyze_upgrade(description="new floor tunnel seal")
        assert result.category in list(UpgradeCategory)
        assert result.component_zone in list(ComponentZone)
        assert result.aero_reasoning
        assert result.mechanical_reasoning
        assert result.performance_hypothesis

    def test_power_unit_upgrade(self):
        result = analyze_upgrade(description="updated turbo with revised mguk energy store mapping")
        assert result.category == UpgradeCategory.POWER_UNIT

    def test_cooling_upgrade(self):
        result = analyze_upgrade(description="new sidepod radiator inlet for improved thermal management")
        assert result.category == UpgradeCategory.COOLING

    def test_signals_deduplicated(self):
        # Signals from category and zone may overlap; result should have no duplicates.
        result = analyze_upgrade(description="front wing downforce and flow improvement")
        assert len(result.signals) == len(set(result.signals))

    def test_all_optional_fields_none(self):
        result = analyze_upgrade(
            description="generic aero update",
            technical_detail=None,
            expected_effect=None,
            source=None,
        )
        assert result.category is not None
        assert result.component_zone is not None

    def test_source_contributes_to_text(self):
        # Source with a zone keyword should influence zone detection.
        result = analyze_upgrade(
            description="aerodynamic update",
            source="diffuser strake revision reported by autosport",
        )
        assert result.component_zone == ComponentZone.DIFFUSER

    def test_drag_description_targets_straight_performance(self):
        result = analyze_upgrade(description="rear wing drag reduction for top speed improvement on straights")
        assert "straight" in result.performance_hypothesis.lower() or "efficiency" in result.performance_hypothesis.lower()

    def test_floor_zone_targets_corner_hypothesis(self):
        result = analyze_upgrade(description="floor edge tunnel fence revision for improved ground effect")
        assert "corner" in result.performance_hypothesis.lower() or "rear load" in result.performance_hypothesis.lower()

    def test_front_wing_zone_targets_front_end_hypothesis(self):
        result = analyze_upgrade(description="front wing flap and nose geometry update")
        assert "front" in result.performance_hypothesis.lower() or "turn-in" in result.performance_hypothesis.lower()

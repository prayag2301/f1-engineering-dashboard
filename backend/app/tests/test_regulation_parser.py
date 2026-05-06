"""
Tests for regulation_parser.py

Run with:
    pytest backend/app/tests/test_regulation_parser.py -v
"""

import pytest
from unittest.mock import patch

from app.app.services.regulation_parser import (
    ParsedConstraint,
    get_static_constraints,
    parse_regulations,
    parse_pdf,
    _classify_component,
    _classify_parameter,
    _normalise_unit,
)


# ---------------------------------------------------------------------------
# Static dataset tests
# ---------------------------------------------------------------------------

class TestStaticConstraints:
    def test_returns_list(self):
        result = get_static_constraints()
        assert isinstance(result, list)

    def test_non_empty(self):
        result = get_static_constraints()
        assert len(result) > 10, "Expected at least 10 static constraints"

    def test_all_are_parsed_constraint(self):
        for item in get_static_constraints():
            assert isinstance(item, ParsedConstraint)

    def test_season_set_correctly(self):
        for item in get_static_constraints(season=2026):
            assert item.season == 2026

    def test_custom_season(self):
        for item in get_static_constraints(season=2027):
            assert item.season == 2027

    def test_components_covered(self):
        components = {c.component for c in get_static_constraints()}
        expected = {"front_wing", "rear_wing", "floor", "diffuser", "overall"}
        assert expected.issubset(components), f"Missing components: {expected - components}"

    def test_only_week4_scope_components_present(self):
        components = {c.component for c in get_static_constraints()}
        assert components.issubset({"front_wing", "rear_wing", "floor", "diffuser", "overall"})

    def test_all_have_article_refs(self):
        for item in get_static_constraints():
            assert item.article_ref and item.article_ref.startswith("Art."), \
                f"Invalid article_ref: {item.article_ref}"

    def test_all_values_positive(self):
        for item in get_static_constraints():
            assert item.value >= 0, f"Negative value for {item.component}.{item.parameter}"

    def test_known_front_wing_width(self):
        """Front wing max width must be 1800 mm per Art. 3.9.1."""
        result = get_static_constraints()
        fw_widths = [
            c for c in result
            if c.component == "front_wing" and c.parameter == "max_width"
        ]
        assert len(fw_widths) == 1
        assert fw_widths[0].value == 1800.0
        assert fw_widths[0].unit == "mm"
        assert fw_widths[0].article_ref == "Art. 3.9.1"

    def test_known_rear_wing_width(self):
        """Rear wing max width must be 1050 mm per Art. 3.10.1."""
        result = get_static_constraints()
        rw_widths = [
            c for c in result
            if c.component == "rear_wing" and c.parameter == "max_width"
        ]
        assert len(rw_widths) == 1
        assert rw_widths[0].value == 1050.0

    def test_known_overall_max_width(self):
        """Overall car max width must be 2000 mm per Art. 2.2."""
        result = get_static_constraints()
        overall = [
            c for c in result
            if c.component == "overall" and c.parameter == "max_width"
        ]
        assert len(overall) == 1
        assert overall[0].value == 2000.0

    def test_known_min_weight(self):
        """Minimum weight must be 800 kg per Art. 4.1."""
        result = get_static_constraints()
        weight = [
            c for c in result
            if c.component == "overall" and c.parameter == "min_weight"
        ]
        assert len(weight) == 1
        assert weight[0].value == 800.0
        assert weight[0].unit == "kg"

    def test_known_drs_max_angle(self):
        """DRS max open angle must be 85 deg per Art. 3.10.5."""
        result = get_static_constraints()
        drs = [
            c for c in result
            if c.component == "rear_wing" and c.parameter == "drs_max_open_angle"
        ]
        assert len(drs) == 1
        assert drs[0].value == 85.0
        assert drs[0].unit == "deg"

    def test_units_are_valid(self):
        valid_units = {"mm", "mm2", "kg", "deg"}
        for item in get_static_constraints():
            assert item.unit in valid_units, f"Unknown unit '{item.unit}' for {item.component}.{item.parameter}"


# ---------------------------------------------------------------------------
# Component classification tests
# ---------------------------------------------------------------------------

class TestClassifyComponent:
    @pytest.mark.parametrize("text, expected", [
        ("The front wing maximum width shall not exceed 1800 mm", "front_wing"),
        ("Rear wing elements are restricted to two per Art. 3.10", "rear_wing"),
        ("The floor assembly including underfloor channels", "floor"),
        ("Diffuser exit height above reference plane", "diffuser"),
        ("Minimum weight of the car including driver", "overall"),
        ("An unrelated sentence with no keywords", None),
    ])
    def test_classification(self, text, expected):
        assert _classify_component(text) == expected


# ---------------------------------------------------------------------------
# Parameter classification tests
# ---------------------------------------------------------------------------

class TestClassifyParameter:
    @pytest.mark.parametrize("text, expected", [
        ("maximum width of the front wing shall not exceed", "max_width"),
        ("maximum height above the reference plane", "max_height_above_ref"),
        ("minimum height of the rear wing lower element", "min_height_above_ref"),
        ("leading edge height on the floor section", "leading_edge_max_height"),
        ("minimum weight including driver and ballast", "min_weight"),
    ])
    def test_parameter_classification(self, text, expected):
        assert _classify_parameter(text, unit="mm") == expected


# ---------------------------------------------------------------------------
# Unit normalisation tests
# ---------------------------------------------------------------------------

class TestNormaliseUnit:
    @pytest.mark.parametrize("raw, expected", [
        ("mm", "mm"),
        ("MM", "mm"),
        ("deg", "deg"),
        ("°", "deg"),
        ("mm2", "mm2"),
        ("mm²", "mm2"),
        ("kg", "kg"),
        ("ratio", "ratio"),
        ("count", "count"),
    ])
    def test_normalise(self, raw, expected):
        assert _normalise_unit(raw) == expected


# ---------------------------------------------------------------------------
# parse_regulations integration tests
# ---------------------------------------------------------------------------

class TestParseRegulations:
    def test_no_pdf_returns_static(self):
        result = parse_regulations(pdf_path=None, season=2026)
        assert len(result) == len(get_static_constraints(2026))

    def test_nonexistent_pdf_returns_static(self):
        result = parse_regulations(pdf_path="/tmp/does_not_exist.pdf", season=2026)
        assert len(result) > 0

    def test_returns_parsed_constraints(self):
        result = parse_regulations()
        for item in result:
            assert isinstance(item, ParsedConstraint)
            assert item.season == 2026
            assert item.value >= 0
            assert item.unit in {"mm", "mm2", "kg", "deg"}

    def test_season_propagated(self):
        result = parse_regulations(season=2025)
        for item in result:
            assert item.season == 2025

    def test_fitz_import_error_falls_back_to_static(self, tmp_path):
        """If PyMuPDF is unavailable, static fallback is used."""
        dummy_pdf = tmp_path / "test.pdf"
        dummy_pdf.write_bytes(b"%PDF-1.4 fake content")

        with patch.dict("sys.modules", {"fitz": None}):
            result = parse_regulations(pdf_path=str(dummy_pdf), season=2026)
        # Falls back to static dataset
        assert len(result) == len(get_static_constraints(2026))

    def test_pdf_parsing_ignores_non_target_component_lines(self, tmp_path):
        pdf = tmp_path / "fake.pdf"
        pdf.write_text("fake")

        class FakePage:
            def get_text(self, _mode: str) -> str:
                return "\n".join(
                    [
                        "Art. 3.9.1 Front wing maximum width 1800 mm",
                        "Art. 3.13.1 Sidepod maximum width 500 mm",
                    ]
                )

        class FakeDoc(list):
            def __init__(self):
                super().__init__([FakePage()])

            def close(self):
                return None

        class FakeFitz:
            @staticmethod
            def open(_path: str):
                return FakeDoc()

        with patch.dict("sys.modules", {"fitz": FakeFitz}):
            parsed = parse_pdf(pdf_path=pdf, season=2026)

        assert any(item.component == "front_wing" for item in parsed)
        assert all("sidepod" not in (item.notes or "").lower() for item in parsed)

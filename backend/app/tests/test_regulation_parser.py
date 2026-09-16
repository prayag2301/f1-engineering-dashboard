import pytest
from app.services.regulation_parser import get_static_constraints, parse_regulations
from app.services.catalog import validate_parameters


def test_reviewed_2026_dimensions_have_article_attribution():
    constraints = get_static_constraints()
    assert len(constraints) == 4
    assert all(
        c.article_ref.startswith("C2.") and c.season == 2026 for c in constraints
    )
    rules = {c.parameter: c for c in constraints}
    assert rules["max_body_half_width"].value == 950
    assert rules["max_wheelbase"].value == 3400
    assert "not the cockpit opening" in rules["min_cockpit_reference_distance"].notes


def test_unreviewed_documents_and_seasons_are_rejected():
    with pytest.raises(ValueError):
        get_static_constraints(2027)
    with pytest.raises(ValueError):
        parse_regulations("unknown.pdf")


@pytest.mark.parametrize(
    "parameters",
    [
        {"chord": 999, "sweep": 0, "camber": 0.02},
        {"chord": 0.25},
        {"chord": 0.25, "sweep": 0, "camber": float("nan")},
    ],
)
def test_unbounded_or_incomplete_geometry_inputs_rejected(parameters):
    with pytest.raises(ValueError):
        validate_parameters("front_wing", parameters)

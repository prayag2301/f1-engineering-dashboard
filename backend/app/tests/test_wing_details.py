import pytest
import trimesh
import copy
import importlib.util
import math

from app.geometry_check import check_wing_attachments
from app.config import get_settings
from app.services.catalog import catalog


@pytest.fixture
def profiles():
    path = get_settings().MODELING_ROOT / "wing_profiles.py"
    spec = importlib.util.spec_from_file_location("wing_profiles", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_camber_controls_preserve_edges_and_move_peak_without_kinks(profiles):
    for peak in (0.25, 0.42, 0.5, 0.75):
        assert profiles.camber_shape(0, peak) == 0
        assert profiles.camber_shape(1, peak) == pytest.approx(0, abs=1e-14)
        assert profiles.camber_shape(peak, peak) == pytest.approx(1)
        left = (
            profiles.camber_shape(peak, peak) - profiles.camber_shape(peak - 1e-6, peak)
        ) / 1e-6
        right = (
            profiles.camber_shape(peak + 1e-6, peak) - profiles.camber_shape(peak, peak)
        ) / 1e-6
        assert abs(left - right) < 0.0001
    for i in range(101):
        t = i / 100
        assert profiles.camber_shape(t) == math.sin(math.pi * t)


@pytest.mark.parametrize(
    "fault", ["duplicate", "nan", "bool", "chord", "peak", "mixed", "shoulder", "fold"]
)
def test_invalid_profile_rejected_before_build(profiles, fault):
    teams = copy.deepcopy(catalog()["teams"])
    shape = teams["mclaren"]["wing_profiles"]["front_wing"]
    rows = shape["mainplane"]
    if fault == "duplicate":
        rows[1][0] = rows[0][0]
    elif fault == "nan":
        rows[0][2] = float("nan")
    elif fault == "bool":
        rows[0][7] = True
    elif fault == "chord":
        rows[0][3] = 0
    elif fault == "peak":
        rows[0][7] = 1
    elif fault == "mixed":
        rows[0].pop()
    elif fault == "shoulder":
        shape["endplate_shoulder"][1][0] += 0.01
    else:
        shape["endplate_shoulder"][1][2] += 0.1
    with pytest.raises(ValueError):
        profiles.validate_wing_profiles(teams)


def test_legacy_profiles_need_no_new_controls(profiles):
    teams = copy.deepcopy(catalog()["teams"])
    for info in teams.values():
        for wing, shape in info.get("wing_profiles", {}).items():
            rows = (
                [shape[k] for k in ("mainplane", "slot_flap", "upper_flap")]
                if wing == "front_wing"
                else shape["profiles"]
            )
            for section in rows:
                for row in section:
                    del row[7:]
            shape.pop("endplate_shoulder", None)
    profiles.validate_wing_profiles(teams)


def test_attachment_checks_support_mesh_not_only_reported_anchor():
    scene = trimesh.Scene()
    for name in ("front_wing.skin", "front_wing.support"):
        scene.add_geometry(
            trimesh.creation.box(extents=(0.02, 0.02, 0.02)), node_name=name
        )
    records = [
        {
            "surface": "front_wing.skin",
            "part": "front_wing.support",
            "anchor": [0.01, 0, 0],
        }
    ]
    check_wing_attachments(scene, records)
    transform, geom = scene.graph["front_wing.support"]
    transform = transform.copy()
    transform[0, 3] = 0.03
    scene.graph.update(frame_to="front_wing.support", matrix=transform, geometry=geom)
    with pytest.raises(AssertionError, match="Detached wing support"):
        check_wing_attachments(scene, records)

import pytest
import trimesh

from app.geometry_check import check_wing_attachments


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

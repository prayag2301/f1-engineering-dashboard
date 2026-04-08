"""
Parametric F1 car model generator — Phase 2, Weeks 5+6.

Generates a complete simplified F1 car mesh from FIA regulation constraints.
Each component is a named mesh node in the exported GLB scene, enabling
per-component annotation and highlighting in the frontend.

Coordinate system (matches the Three.js frontend model):
  - 1 unit = 1 metre
  - Y-up, nose at -Z, rear at +Z
  - Wheels sit on Y = 0

Usage:
    python -m app.services.model_generator --team red-bull --output /tmp/car.glb
    python -m app.services.model_generator --team ferrari --season 2026 --output /tmp/ferrari.glb
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np
import trimesh
import trimesh.transformations as tf
from trimesh.visual.material import PBRMaterial

# ── Regulation constants (mm → m) ─────────────────────────────────────────────
# Sourced from STATIC_CONSTRAINTS_2026 in regulation_parser.py
REG = {
    "car_length":        5.700,   # Art. 2.1  max overall length
    "car_width":         2.000,   # Art. 2.2  max overall width
    "car_height":        1.000,   # Art. 2.3  max overall height
    "fw_width":          1.800,   # Art. 3.9.1  front wing width
    "fw_max_height":     0.400,   # Art. 3.9.3  front wing max height above ref
    "fw_overhang":       1.000,   # Art. 3.9.2  max front overhang
    "rw_width":          1.050,   # Art. 3.10.1 rear wing width
    "rw_max_height":     0.950,   # Art. 3.10.2 rear wing max height
    "rw_min_height":     0.750,   # Art. 3.10.3 rear wing min height
    "rw_chord":          0.500,   # Art. 3.10.4 rear wing max chord
    "floor_width":       1.600,   # Art. 3.11.1 floor width
    "diffuser_width":    1.050,   # Art. 3.12.1 diffuser width
    "diffuser_height":   0.350,   # Art. 3.12.2 diffuser exit height
}

# ── Team liveries ──────────────────────────────────────────────────────────────
# RGB tuples (0–255), mirroring TEAM_LIVERIES in F1CarModel.tsx
TEAM_LIVERIES: dict[str, dict[str, tuple[int, int, int]]] = {
    "red-bull":     {"primary": (12,  26,  62),  "secondary": (255, 215,   0), "accent": (204,   0,   1)},
    "ferrari":      {"primary": (232,  0,  45),  "secondary": (255, 255, 255), "accent": (255, 242,   0)},
    "mercedes":     {"primary": (0,  210, 190),  "secondary": ( 28,  28,  28), "accent": (255, 255, 255)},
    "mclaren":      {"primary": (255, 128,  0),  "secondary": ( 15,  15,  15), "accent": (255, 255, 255)},
    "aston-martin": {"primary": (0,  111,  98),  "secondary": (206, 220,   0), "accent": (255, 255, 255)},
    "alpine":       {"primary": (0,  147, 204),  "secondary": (228,   0, 120), "accent": (255, 255, 255)},
    "williams":     {"primary": (0,   90, 255),  "secondary": (255, 255, 255), "accent": (228,   0,  32)},
    "racing-bulls": {"primary": (30,  65, 183),  "secondary": (204,   0,   0), "accent": (255, 255, 255)},
    "haas":         {"primary": (232,  0,  45),  "secondary": (255, 255, 255), "accent": (182, 186, 189)},
    "audi":         {"primary": ( 28,  28,  28), "secondary": (191,   0,   0), "accent": (255, 255, 255)},
    "cadillac":     {"primary": ( 10,  10,  10), "secondary": (181, 149, 106), "accent": (255, 255, 255)},
}
DEFAULT_LIVERY = TEAM_LIVERIES["red-bull"]


# ── Material helpers ───────────────────────────────────────────────────────────

def _rgb01(rgb: tuple[int, int, int]) -> list[float]:
    return [rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0, 1.0]


def _mat(color: tuple[int, int, int], roughness: float = 0.3, metalness: float = 0.5) -> PBRMaterial:
    return PBRMaterial(
        baseColorFactor=np.array(_rgb01(color), dtype=float),
        roughnessFactor=roughness,
        metallicFactor=metalness,
    )


def _apply_mat(mesh: trimesh.Trimesh, material: PBRMaterial) -> trimesh.Trimesh:
    mesh.visual = trimesh.visual.TextureVisuals(material=material)
    return mesh


# ── Geometry primitives ────────────────────────────────────────────────────────

def _box(
    w: float, h: float, d: float,
    pos: tuple[float, float, float] = (0, 0, 0),
    rot_x: float = 0.0, rot_y: float = 0.0, rot_z: float = 0.0,
) -> trimesh.Trimesh:
    """Axis-aligned box centered at origin, then positioned."""
    mesh = trimesh.creation.box(extents=[w, h, d])
    if rot_x:
        mesh.apply_transform(tf.rotation_matrix(rot_x, [1, 0, 0]))
    if rot_y:
        mesh.apply_transform(tf.rotation_matrix(rot_y, [0, 1, 0]))
    if rot_z:
        mesh.apply_transform(tf.rotation_matrix(rot_z, [0, 0, 1]))
    mesh.apply_translation(pos)
    return mesh


def _cylinder_y(
    radius: float, height: float, sections: int = 24,
    pos: tuple[float, float, float] = (0, 0, 0),
    rot_x: float = 0.0,
) -> trimesh.Trimesh:
    """Cylinder with axis along Y (matching Three.js CylinderGeometry default)."""
    mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    # trimesh cylinder is along Z; rotate -90° around X → Z becomes +Y
    mesh.apply_transform(tf.rotation_matrix(-math.pi / 2, [1, 0, 0]))
    if rot_x:
        mesh.apply_transform(tf.rotation_matrix(rot_x, [1, 0, 0]))
    mesh.apply_translation(pos)
    return mesh


def _cylinder_x(
    radius: float, height: float, sections: int = 24,
    pos: tuple[float, float, float] = (0, 0, 0),
) -> trimesh.Trimesh:
    """Cylinder with axis along X (for wheels: rotate 90° around Y to go Z→X)."""
    mesh = trimesh.creation.cylinder(radius=radius, height=height, sections=sections)
    # rotate 90° around Y → Z becomes +X
    mesh.apply_transform(tf.rotation_matrix(math.pi / 2, [0, 1, 0]))
    mesh.apply_translation(pos)
    return mesh


def _frustum_y(
    r_top: float, r_bottom: float, height: float,
    sections: int = 16,
    pos: tuple[float, float, float] = (0, 0, 0),
    rot_x: float = 0.0,
) -> trimesh.Trimesh:
    """Truncated cone (frustum) with axis along Y — no trimesh built-in, built manually."""
    n = sections
    angles = np.linspace(0, 2 * math.pi, n, endpoint=False)

    cos_a = np.cos(angles)
    sin_a = np.sin(angles)
    half_h = height / 2.0

    # vertices: bottom_center(0), top_center(1), bottom_ring(2..n+1), top_ring(n+2..2n+1)
    verts = np.zeros((2 + 2 * n, 3))
    verts[0] = [0, -half_h, 0]   # bottom center
    verts[1] = [0,  half_h, 0]   # top center
    for i in range(n):
        verts[2 + i]     = [r_bottom * cos_a[i], -half_h, r_bottom * sin_a[i]]
        verts[2 + n + i] = [r_top    * cos_a[i],  half_h, r_top    * sin_a[i]]

    faces = []
    for i in range(n):
        ni = (i + 1) % n
        bi, bni = 2 + i, 2 + ni
        ti, tni = 2 + n + i, 2 + n + ni
        faces.append([0,  bni, bi ])   # bottom cap
        faces.append([1,  ti,  tni])   # top cap
        faces.append([bi, bni, ti ])   # side tri 1
        faces.append([bni, tni, ti])   # side tri 2

    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces))
    if rot_x:
        mesh.apply_transform(tf.rotation_matrix(rot_x, [1, 0, 0]))
    mesh.apply_translation(pos)
    return mesh


# ── Component builders ─────────────────────────────────────────────────────────

@dataclass
class CarColors:
    body:    tuple[int, int, int]
    accent:  tuple[int, int, int]
    wing:    tuple[int, int, int]
    sidepod: tuple[int, int, int]
    tire:    tuple[int, int, int] = (26,  26,  26)
    rim:     tuple[int, int, int] = (192, 192, 192)
    floor:   tuple[int, int, int] = (13,  13,  13)
    halo:    tuple[int, int, int] = (28,  28,  28)
    inlet:   tuple[int, int, int] = (8,   8,   8)


def _colors_for_team(team_id: str) -> CarColors:
    liv = TEAM_LIVERIES.get(team_id, DEFAULT_LIVERY)
    rim_color = liv["accent"] if liv["accent"] != (255, 255, 255) else (192, 192, 192)
    return CarColors(
        body=liv["primary"],
        accent=liv["secondary"],
        wing=liv["primary"],
        sidepod=liv["secondary"],
        rim=rim_color,
    )


def _build_floor(c: CarColors, regs: dict) -> dict[str, trimesh.Trimesh]:
    mat_floor = _mat(c.floor, roughness=0.35, metalness=0.4)
    fw = regs["floor_width"]
    parts: dict[str, trimesh.Trimesh] = {}

    # Main floor plate
    m = _box(fw * 0.9, 0.04, 3.8, pos=(0, 0.095, -0.1))
    parts["floor_plate"] = _apply_mat(m, mat_floor)

    # Diffuser
    dw = regs["diffuser_width"]
    dh = regs["diffuser_height"]
    m = _box(dw * 0.9, 0.04, 0.8, pos=(0, 0.18, 2.0), rot_x=-0.35)
    parts["diffuser"] = _apply_mat(m, mat_floor)

    return parts


def _build_body(c: CarColors) -> dict[str, trimesh.Trimesh]:
    mat_body   = _mat(c.body,   roughness=0.25, metalness=0.55)
    mat_accent = _mat(c.accent, roughness=0.2,  metalness=0.6)
    mat_halo   = _mat(c.halo,   roughness=0.2,  metalness=0.8)
    mat_inlet  = _mat(c.inlet,  roughness=0.5,  metalness=0.3)
    mat_side   = _mat(c.sidepod, roughness=0.25, metalness=0.5)
    parts: dict[str, trimesh.Trimesh] = {}

    # Monocoque lower
    m = _box(0.46, 0.28, 1.9, pos=(0, 0.265, -0.3))
    parts["monocoque_lower"] = _apply_mat(m, mat_body)

    # Monocoque upper fairing
    m = _box(0.24, 0.14, 0.9, pos=(0, 0.44, -0.35))
    parts["monocoque_upper"] = _apply_mat(m, mat_body)

    # Nose cone (frustum: narrow at front, wider at monocoque join)
    m = _frustum_y(r_top=0.09, r_bottom=0.035, height=1.55, sections=16,
                   pos=(0, 0.29, -1.625), rot_x=0.06)
    parts["nose_cone"] = _apply_mat(m, mat_body)

    # Sidepods
    for side, sx in (("l", -1), ("r", 1)):
        m = _box(0.34, 0.38, 1.75, pos=(sx * 0.44, 0.27, 0.25))
        parts[f"sidepod_{side}"] = _apply_mat(m, mat_side)

        m = _box(0.28, 0.22, 0.04, pos=(sx * 0.44, 0.3, -0.565))
        parts[f"sidepod_inlet_{side}"] = _apply_mat(m, mat_inlet)

    # Engine cover / shark fin
    m = _box(0.055, 0.72, 1.3, pos=(0, 0.73, 0.7))
    parts["engine_cover"] = _apply_mat(m, mat_accent)

    # Roll hoop
    m = _box(0.38, 0.08, 0.1, pos=(0, 0.75, 0.1))
    parts["roll_hoop_bar"] = _apply_mat(m, mat_halo)
    for side, sx in (("l", -1), ("r", 1)):
        m = _box(0.06, 0.2, 0.08, pos=(sx * 0.19, 0.82, 0.1))
        parts[f"roll_hoop_pillar_{side}"] = _apply_mat(m, mat_halo)

    # Halo central pillar
    m = _cylinder_y(0.025, 0.62, sections=8, pos=(0, 0.52, -0.55))
    parts["halo_pillar"] = _apply_mat(m, mat_halo)

    # Halo arch
    m = _box(0.52, 0.04, 0.72, pos=(0, 0.82, -0.15))
    parts["halo_arch_top"] = _apply_mat(m, mat_halo)
    for side, sx in (("l", -1), ("r", 1)):
        m = _box(0.04, 0.34, 0.72, pos=(sx * 0.26, 0.66, -0.15))
        parts[f"halo_arch_{side}"] = _apply_mat(m, mat_halo)

    # Brake ducts
    for side, sx in (("l", -1), ("r", 1)):
        m = _box(0.22, 0.2, 0.15, pos=(sx * 0.72, 0.335, -1.8))
        parts[f"brake_duct_{side}"] = _apply_mat(m, mat_inlet)

    return parts


def _build_front_wing(c: CarColors, regs: dict) -> dict[str, trimesh.Trimesh]:
    mat_wing   = _mat(c.wing,   roughness=0.2,  metalness=0.5)
    mat_accent = _mat(c.accent, roughness=0.2,  metalness=0.6)
    parts: dict[str, trimesh.Trimesh] = {}

    fw = regs["fw_width"]   # 1.8 m

    # Main plane
    m = _box(fw,      0.058, 0.32, pos=(0, 0.11, -2.28))
    parts["fw_main"] = _apply_mat(m, mat_wing)

    # Flap 1
    m = _box(fw*0.956, 0.045, 0.24, pos=(0, 0.19, -2.23), rot_x=-0.08)
    parts["fw_flap1"] = _apply_mat(m, mat_wing)

    # Flap 2
    m = _box(fw*0.917, 0.038, 0.18, pos=(0, 0.26, -2.18), rot_x=-0.12)
    parts["fw_flap2"] = _apply_mat(m, mat_wing)

    # Nose attachment pillar
    m = _box(0.12, 0.2, 0.35, pos=(0, 0.15, -2.3))
    parts["fw_nose_attach"] = _apply_mat(m, mat_accent)

    # Endplates
    for side, sx in (("l", -fw/2), ("r", fw/2)):
        m = _box(0.022, 0.2, 0.36, pos=(sx, 0.15, -2.28))
        parts[f"fw_endplate_{side}"] = _apply_mat(m, mat_accent)

    # Cascades (canards)
    for side, sx in (("l", -fw/2), ("r", fw/2)):
        m = _box(0.22, 0.055, 0.025, pos=(sx, 0.22, -2.28))
        parts[f"fw_cascade_{side}"] = _apply_mat(m, mat_wing)

    return parts


def _build_rear_wing(c: CarColors, regs: dict) -> dict[str, trimesh.Trimesh]:
    mat_wing   = _mat(c.wing,   roughness=0.2,  metalness=0.5)
    mat_accent = _mat(c.accent, roughness=0.2,  metalness=0.6)
    parts: dict[str, trimesh.Trimesh] = {}

    rw = regs["rw_width"]          # 1.05 m
    rw_h_max = regs["rw_max_height"]  # 0.95 m (used for positioning)

    # Main plane
    m = _box(rw, 0.065, 0.3, pos=(0, 0.895, 2.05))
    parts["rw_main"] = _apply_mat(m, mat_wing)

    # Flap (DRS)
    m = _box(rw * 0.857, 0.052, 0.24, pos=(0, 0.985, 2.0), rot_x=-0.1)
    parts["rw_flap"] = _apply_mat(m, mat_wing)

    # Endplates
    for side, sx in (("l", -rw/2 + 0.025), ("r", rw/2 - 0.025)):
        m = _box(0.022, 0.28, 0.34, pos=(sx, 0.895, 2.02))
        parts[f"rw_endplate_{side}"] = _apply_mat(m, mat_accent)

    # Beam wing
    m = _box(0.45, 0.04, 0.2, pos=(0, 0.58, 1.95))
    parts["rw_beam"] = _apply_mat(m, mat_wing)

    # Pylons
    for side, sx in (("l", -0.2), ("r", 0.2)):
        m = _box(0.06, 0.28, 0.065, pos=(sx, 0.74, 2.02))
        parts[f"rw_pylon_{side}"] = _apply_mat(m, mat_accent)

    return parts


def _build_suspension(c: CarColors) -> dict[str, trimesh.Trimesh]:
    mat_halo = _mat(c.halo, roughness=0.2, metalness=0.8)
    parts: dict[str, trimesh.Trimesh] = {}

    # Front wishbones (upper + lower, both sides)
    wishbone_defs = [
        ("front_upper_l", (-0.52, 0.48, -1.8), ( 0.35, 0.18)),
        ("front_upper_r", ( 0.52, 0.48, -1.8), (-0.35, -0.18)),
        ("front_lower_l", (-0.52, 0.22, -1.8), ( 0.28, -0.08)),
        ("front_lower_r", ( 0.52, 0.22, -1.8), (-0.28,  0.08)),
        ("rear_upper_l",  (-0.52, 0.48,  1.8), (-0.28,  0.18)),
        ("rear_upper_r",  ( 0.52, 0.48,  1.8), ( 0.28, -0.18)),
    ]
    for name, pos, (ry, rz) in wishbone_defs:
        m = _box(0.52, 0.025, 0.025, pos=pos, rot_y=ry, rot_z=rz)
        parts[f"wishbone_{name}"] = _apply_mat(m, mat_halo)

    return parts


def _build_wheels(c: CarColors) -> dict[str, trimesh.Trimesh]:
    mat_tire = _mat(c.tire, roughness=0.9, metalness=0.0)
    mat_rim  = _mat(c.rim,  roughness=0.15, metalness=0.85)
    parts: dict[str, trimesh.Trimesh] = {}

    tire_r = 0.335
    wheel_defs = [
        ("fl", -0.88, -1.8, True),
        ("fr",  0.88, -1.8, True),
        ("rl", -0.80,  1.8, False),
        ("rr",  0.80,  1.8, False),
    ]
    for tag, wx, wz, is_front in wheel_defs:
        tire_w = 0.305 if is_front else 0.405
        rim_r  = 0.225
        wy = tire_r  # sit on Y=0

        # Tire
        m = _cylinder_x(tire_r, tire_w, sections=32, pos=(wx, wy, wz))
        parts[f"tire_{tag}"] = _apply_mat(m, mat_tire)

        # Rim
        m = _cylinder_x(rim_r, tire_w + 0.01, sections=16, pos=(wx, wy, wz))
        parts[f"rim_{tag}"] = _apply_mat(m, mat_rim)

        # Hub centre
        hub_offset = 0.01 if wx > 0 else -0.01
        m = _cylinder_x(0.09, 0.03, sections=16, pos=(wx + hub_offset, wy, wz))
        parts[f"hub_{tag}"] = _apply_mat(m, mat_rim)

    return parts


# ── Top-level generator ────────────────────────────────────────────────────────

def generate_car_glb(
    team_id: str = "red-bull",
    season: int = 2026,
    deform_params: dict | None = None,
) -> bytes:
    """
    Generate a full parametric F1 car GLB for the given team.

    Args:
        team_id:       Team identifier (e.g. "red-bull", "ferrari")
        season:        Season year — selects regulation set
        deform_params: Optional per-component scale/translate overrides from
                       mesh_deformer.py (Week 7).

    Returns:
        Raw GLB bytes ready to serve or cache to disk.
    """
    colors = _colors_for_team(team_id)
    regs   = REG.copy()   # Could be swapped for DB-sourced constraints in future

    # Build all component groups
    all_parts: dict[str, trimesh.Trimesh] = {}
    all_parts.update(_build_floor(colors, regs))
    all_parts.update(_build_body(colors))
    all_parts.update(_build_front_wing(colors, regs))
    all_parts.update(_build_rear_wing(colors, regs))
    all_parts.update(_build_suspension(colors))
    all_parts.update(_build_wheels(colors))

    # Apply team-specific deformation overrides (Week 7)
    if deform_params:
        for comp_name, ops in deform_params.items():
            if comp_name not in all_parts:
                continue
            mesh = all_parts[comp_name]
            if "scale" in ops:
                sx, sy, sz = ops["scale"]
                scale_mat = np.diag([sx, sy, sz, 1.0])
                mesh.apply_transform(scale_mat)
            if "translate" in ops:
                mesh.apply_translation(ops["translate"])

    # Assemble scene with named nodes
    scene = trimesh.Scene()
    for name, mesh in all_parts.items():
        scene.add_geometry(mesh, geom_name=name, node_name=name)

    return scene.export(file_type="glb")


def generate_and_save(
    team_id: str,
    output_path: str | Path,
    season: int = 2026,
    deform_params: dict | None = None,
) -> Path:
    """Generate a GLB and write to disk. Returns the output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    glb_bytes = generate_car_glb(team_id=team_id, season=season, deform_params=deform_params)
    path.write_bytes(glb_bytes)
    return path


# ── CLI ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Generate a parametric F1 car GLB.")
    p.add_argument("--team",   default="red-bull", help="Team ID (e.g. red-bull, ferrari)")
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--output", default="/tmp/f1_car.glb")
    args = p.parse_args()

    out = generate_and_save(team_id=args.team, output_path=args.output, season=args.season)
    size_kb = out.stat().st_size / 1024
    print(f"Generated {out}  ({size_kb:.1f} KB)")

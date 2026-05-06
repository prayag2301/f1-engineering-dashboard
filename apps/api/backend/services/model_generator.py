"""
model_generator.py
------------------
Week 5 — Parametric front wing skeleton from FIA regulation constraints.

Reads RegulationConstraint rows from the database for the requested
component + season, then builds a multi-element trimesh.Scene and
exports it as a .glb file.

Supported components (Week 5 scope):
  front_wing — mainplane + 2 flaps + 2 endplates

Usage (CLI):
  # Inside Docker:
  docker exec <api-container> python -m backend.services.model_generator \\
      --component front_wing --season 2026

  # Locally (outside Docker):
  cd apps/api
  DATABASE_URL=postgresql://f1user:f1pass@localhost:5432/f1dashboard \\
      python -m backend.services.model_generator --component front_wing --season 2026
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import trimesh

logger = logging.getLogger(__name__)

# Generated GLBs are written here — inside the volume-mounted backend package
# so files persist on the host at ./apps/api/backend/generated_models/
_MODELS_DIR = Path(__file__).resolve().parents[1] / "generated_models"

SUPPORTED_COMPONENTS = {"front_wing"}


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------

def _m(mm: float) -> float:
    """Convert mm → metres (glTF/Three.js scale: 1 unit = 1 m)."""
    return mm / 1000.0


# ---------------------------------------------------------------------------
# Front wing builder
# ---------------------------------------------------------------------------

def _build_front_wing(c: dict) -> trimesh.Scene:
    """
    Construct a multi-element front wing that fits within the FIA bounding box.

    Named mesh nodes (important for later annotation targeting in Week 10):
      front_wing_mainplane     — widest, lowest element
      front_wing_flap1         — intermediate element
      front_wing_flap2         — topmost, narrowest element
      front_wing_endplate_l    — left endplate
      front_wing_endplate_r    — right endplate

    Coordinate system matches the existing procedural car:
      X = lateral (right = +X), Y = vertical (up = +Y), Z = longitudinal (rear = +Z)
    Wing sits at the nose (negative Z), centred at X = 0.
    """
    # Regulation limits in metres
    max_width_m    = _m(c.get("max_width",            1800.0))   # 1.80 m
    max_height_m   = _m(c.get("max_height_above_ref",  400.0))   # 0.40 m
    max_overhang_m = _m(c.get("max_forward_overhang", 1000.0))   # 1.00 m

    # Geometry — stay comfortably inside the regulation envelope
    half_span   = max_width_m   * 0.48    # 0.864 m per side
    total_depth = max_overhang_m * 0.60   # 0.60 m front-to-back

    ep_thickness = _m(12.0)               # endplate skin: 12 mm
    ep_height    = max_height_m * 0.70    # 0.28 m

    # --- Mainplane (lowest, widest) ---
    mp_chord = total_depth * 0.44         # 0.264 m
    mp_thick = _m(32.0)
    mp_y     = _m(50.0)                   # 50 mm ground clearance
    mp_z     = -(total_depth / 2) + (mp_chord / 2)

    # --- Flap 1 (intermediate) ---
    f1_span  = half_span * 2 * 0.84
    f1_chord = total_depth * 0.28
    f1_thick = _m(22.0)
    f1_y     = mp_y + mp_thick + _m(40.0)
    f1_z     = mp_z + (mp_chord / 2) + _m(10.0) + (f1_chord / 2)

    # --- Flap 2 (topmost, narrowest) ---
    f2_span  = half_span * 2 * 0.68
    f2_chord = total_depth * 0.20
    f2_thick = _m(16.0)
    f2_y     = f1_y + f1_thick + _m(35.0)
    f2_z     = f1_z + (f1_chord / 2) + _m(8.0) + (f2_chord / 2)

    # --- Endplates ---
    ep_z_front  = mp_z - (mp_chord / 2)
    ep_z_rear   = f2_z + (f2_chord / 2)
    ep_chord    = ep_z_rear - ep_z_front
    ep_z_centre = ep_z_front + ep_chord / 2

    # Build geometry
    mainplane = trimesh.creation.box(extents=[half_span * 2, mp_thick, mp_chord])
    mainplane.apply_translation([0, mp_y + mp_thick / 2, mp_z])

    flap1 = trimesh.creation.box(extents=[f1_span, f1_thick, f1_chord])
    flap1.apply_translation([0, f1_y + f1_thick / 2, f1_z])

    flap2 = trimesh.creation.box(extents=[f2_span, f2_thick, f2_chord])
    flap2.apply_translation([0, f2_y + f2_thick / 2, f2_z])

    ep_l = trimesh.creation.box(extents=[ep_thickness, ep_height, ep_chord])
    ep_l.apply_translation([-half_span, ep_height / 2, ep_z_centre])

    ep_r = trimesh.creation.box(extents=[ep_thickness, ep_height, ep_chord])
    ep_r.apply_translation([half_span, ep_height / 2, ep_z_centre])

    # Vertex colours — dark carbon fibre tones
    colours: dict[str, list[int]] = {
        "front_wing_mainplane":  [20, 20, 20, 255],
        "front_wing_flap1":      [28, 28, 28, 255],
        "front_wing_flap2":      [35, 35, 35, 255],
        "front_wing_endplate_l": [15, 15, 15, 255],
        "front_wing_endplate_r": [15, 15, 15, 255],
    }
    meshes: dict[str, trimesh.Trimesh] = {
        "front_wing_mainplane":  mainplane,
        "front_wing_flap1":      flap1,
        "front_wing_flap2":      flap2,
        "front_wing_endplate_l": ep_l,
        "front_wing_endplate_r": ep_r,
    }
    for name, mesh in meshes.items():
        rgba = colours[name]
        mesh.visual.vertex_colors = np.tile(rgba, (len(mesh.vertices), 1)).astype(np.uint8)

    return trimesh.Scene(geometry=meshes)


# ---------------------------------------------------------------------------
# Constraint loading
# ---------------------------------------------------------------------------

def _load_constraints(component: str, season: int, db=None) -> dict:
    """
    Return {parameter: value} for *component* + *season* from the DB.
    Falls back to hardcoded 2026 values if DB is unavailable or has no rows.
    """
    _STATIC: dict[str, dict] = {
        "front_wing": {
            "max_width":            1800.0,
            "max_height_above_ref":  400.0,
            "max_forward_overhang": 1000.0,
            "max_camber_angle":       25.0,
        }
    }

    close_db = db is None
    if close_db:
        try:
            from app.database import SessionLocal
        except ModuleNotFoundError:
            from backend.database import SessionLocal
        db = SessionLocal()

    try:
        try:
            from app.models.models import RegulationConstraint
        except ModuleNotFoundError:
            from backend.models.models import RegulationConstraint

        rows = (
            db.query(RegulationConstraint)
            .filter(
                RegulationConstraint.season    == season,
                RegulationConstraint.component == component,
            )
            .all()
        )
        if rows:
            return {r.parameter: r.value for r in rows}
        logger.warning(
            "No DB constraints for %s/%s — using static fallback.", component, season
        )
    except Exception as exc:
        logger.warning("DB unavailable (%s) — using static fallback.", exc)
    finally:
        if close_db:
            db.close()

    return _STATIC.get(component, {})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_model(
    component: str,
    season: int = 2026,
    output_path: Optional[Path] = None,
    db=None,
) -> Path:
    """
    Generate a parametric .glb for *component* at *season* regulation spec.

    Parameters
    ----------
    component   : "front_wing" (Week 5 scope)
    season      : regulation year, default 2026
    output_path : explicit output path; defaults to generated_models/{component}_{season}.glb
    db          : SQLAlchemy Session (opened/closed automatically if None)

    Returns
    -------
    Path to the written .glb file.
    """
    if component not in SUPPORTED_COMPONENTS:
        raise NotImplementedError(
            f"'{component}' is not yet supported. "
            f"Week 5 scope: {sorted(SUPPORTED_COMPONENTS)}."
        )

    constraints = _load_constraints(component=component, season=season, db=db)
    logger.debug("Constraints for %s/%s: %s", component, season, constraints)

    if component == "front_wing":
        scene = _build_front_wing(constraints)

    if output_path is None:
        _MODELS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = _MODELS_DIR / f"{component}_{season}.glb"

    glb_bytes = scene.export(file_type="glb")
    output_path.write_bytes(glb_bytes)
    logger.info("Wrote %d bytes → %s", len(glb_bytes), output_path)
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    parser = argparse.ArgumentParser(
        description="Generate a parametric F1 component model from regulation constraints."
    )
    parser.add_argument(
        "--component",
        default="front_wing",
        choices=sorted(SUPPORTED_COMPONENTS),
        help="Component to generate (default: front_wing)",
    )
    parser.add_argument(
        "--season",
        type=int,
        default=2026,
        help="Regulation season year (default: 2026)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output .glb path (default: generated_models/{component}_{season}.glb)",
    )
    args = parser.parse_args()

    path = generate_model(
        component=args.component,
        season=args.season,
        output_path=args.output,
    )
    print(f"Generated: {path}")

"""Blender-independent controls shared by authoring validation and frozen builds."""

import math


def camber_shape(t, peak=0.5):
    # The rational remap moves the maximum without a kink or moving either edge.
    phase = t if peak == 0.5 else (1 - peak) * t / (peak + (1 - 2 * peak) * t)
    return math.sin(math.pi * phase)


def validate_wing_profiles(teams):
    for team, info in teams.items():
        for wing, shape in info.get("wing_profiles", {}).items():
            label = f"{team}.{wing}"
            profiles = (
                [shape[k] for k in ("mainplane", "slot_flap", "upper_flap")]
                if wing == "front_wing"
                else shape["profiles"]
            )
            for rows in profiles:
                _rows(rows, (7, 8), label)
                if rows[0][0] < 0 or any(r[3] <= 0 or r[6] <= 0 for r in rows):
                    raise ValueError(f"{label}: span, chord and thickness are invalid")
                if len(rows[0]) == 8 and any(not 0.25 <= r[7] <= 0.75 for r in rows):
                    raise ValueError(
                        f"{label}: camber peak must be between 0.25 and 0.75"
                    )
            _rows(shape["endplate"], (7,), label)
            shoulder = shape.get("endplate_shoulder")
            if shoulder is not None:
                _rows(shoulder, (4,), label)
                if [r[0] for r in shoulder] != [r[0] for r in shape["endplate"]]:
                    raise ValueError(f"{label}: shoulder stations must match endplate")
                for edge, middle in zip(shape["endplate"], shoulder):
                    # Limit this first patch model to a lateral shoulder: no folded rails.
                    center = [(a + b) / 2 for a, b in zip(edge[1:4], edge[4:7])]
                    if (
                        abs(middle[1] - center[0]) > 0.02
                        or abs(middle[2] - center[1]) > 1e-8
                        or abs(middle[3] - center[2]) > 1e-8
                    ):
                        raise ValueError(
                            f"{label}: shoulder must stay within the lateral envelope"
                        )


def _rows(rows, widths, label):
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValueError(f"{label}: at least two stations are required")
    if any(not isinstance(r, list) or len(r) not in widths for r in rows):
        raise ValueError(f"{label}: invalid station columns")
    if len({len(r) for r in rows}) != 1 or any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for r in rows
        for v in r
    ):
        raise ValueError(f"{label}: stations must have consistent finite coordinates")
    if any(a[0] >= b[0] for a, b in zip(rows, rows[1:])):
        raise ValueError(f"{label}: stations must be strictly increasing")

"""Original editable F1 exterior reconstruction. Run with Blender, not CPython.

blender --background --python-exit-code 1 --python build_car.py -- --input spec.json --output DIR
All builder coordinates: metres, X lateral, Y up, Z rearwards. V converts to
Blender Z-up; the standard glTF exporter restores the declared car coordinates.
No team CAD, game assets, or scraped sponsor textures are used.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np

PI = math.pi
CAR_OBJECTS = []
COMPONENT = "chassis"


def V(point):
    x, y, z = point
    return Vector((x, -z, y))


def register(obj, name, material, smooth=True):
    obj.name = COMPONENT + "." + name
    obj["component"] = COMPONENT
    obj["reconstruction"] = (
        "public-reference exterior; dimensions estimated unless cited"
    )
    if material:
        obj.data.materials.append(material)
    if obj.type == "MESH" and smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    CAR_OBJECTS.append(obj)
    return obj


def mesh(name, verts, faces, material, subdivision=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata([V(v) for v in verts], [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    register(obj, name, material)
    if subdivision:
        modifier = obj.modifiers.new("Surface continuity", "SUBSURF")
        modifier.levels = subdivision
        modifier.render_levels = subdivision
    return obj


def uv_project(obj):
    if obj.type != "MESH":
        return
    uv = obj.data.uv_layers.new(name="SurfaceUV")
    for polygon in obj.data.polygons:
        for index in polygon.loop_indices:
            vert = obj.data.vertices[obj.data.loops[index].vertex_index].co
            uv.data[index].uv = (vert.y * 20, vert.x * 20 + vert.z * 20)


def material(name, color, roughness=0.3, metallic=0, coat=0, texture=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = 0.22
    if texture is not None:
        image_node = m.node_tree.nodes.new("ShaderNodeTexImage")
        image_node.image = texture
        m.node_tree.links.new(image_node.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def weave_texture():
    # Original 2x2 twill weave; packed into the .blend and GLB.
    n = 256
    y, x = np.mgrid[0:n, 0:n]
    tx, ty = x // 16, y // 16
    over = (tx + ty) % 4 < 2
    ridges = np.where(over, np.sin((x % 16) / 16 * PI), np.sin((y % 16) / 16 * PI))
    fibers = np.where(over, np.cos(x * PI), np.cos(y * PI))
    shade = 0.035 + 0.035 * ridges + 0.004 * fibers
    pixels = np.ones((n, n, 4), dtype=np.float32)
    pixels[:, :, :3] = shade[:, :, None]
    image = bpy.data.images.new("Original carbon twill", width=n, height=n)
    image.pixels.foreach_set(pixels.ravel())
    image.pack()
    return image


def loft(name, sections, mat, offset=0, exponent=0.78, subdivisions=2, cap=True):
    # Sections: longitudinal Z, half-width, centre-height, half-height.
    verts, faces = [], []
    n = 24
    for section in sections:
        z, width, cy, height = section[:4]
        centre_x = section[4] if len(section) > 4 else offset
        for j in range(n):
            t = j * 2 * PI / n
            sx, sy = math.sin(t), math.cos(t)
            verts.append(
                (
                    centre_x + width * math.copysign(abs(sx) ** exponent, sx),
                    cy + height * math.copysign(abs(sy) ** exponent, sy),
                    z,
                )
            )
    for i in range(len(sections) - 1):
        for j in range(n):
            a = i * n + j
            b = i * n + (j + 1) % n
            faces.append((a, b, b + n, a + n))
    if cap:
        faces += [
            tuple(reversed(range(n))),
            tuple((len(sections) - 1) * n + j for j in range(n)),
        ]
    # Section loops run clockwise in X/Y; reverse to point outside the shell.
    return mesh(
        name, verts, [tuple(reversed(face)) for face in faces], mat, subdivisions
    )


def tube(name, points, radius, mat, resolution=12, cyclic=False):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = resolution
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for p, co in zip(spline.bezier_points, points):
        p.co = V(co)
        p.handle_left_type = "AUTO"
        p.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    return register(obj, name, mat)


def rod(name, a, b, radius, mat, vertices=12):
    va, vb = V(a), V(b)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=(vb - va).length, location=(va + vb) / 2
    )
    obj = bpy.context.object
    obj.rotation_euler = (vb - va).to_track_quat("Z", "Y").to_euler()
    return register(obj, name, mat)


def paint_ribbon(name, points, width, mat, surface):
    """Thin original livery paint, projected onto the subdivided body surface."""
    bpy.context.view_layer.update()
    tree = BVHTree.FromObject(surface, bpy.context.evaluated_depsgraph_get())
    path = []
    for a, b in zip(points, points[1:]):
        va, vb = V(a), V(b)
        path.extend(va.lerp(vb, i / 30) for i in range(30))
    path.append(V(points[-1]))
    verts = []
    for i, point in enumerate(path):
        location, normal, _, _ = tree.find_nearest(point)
        tangent = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]
        across = normal.cross(tangent).normalized() * width * 0.5
        for direction in np.linspace(-1, 1, 7):
            hit, n, _, _ = tree.find_nearest(location + across * direction)
            co = hit + n * 0.0008
            verts.append((co.x, co.z, -co.y))
    # Subdivide across as well as along the stripe: a wide flat quad would cut
    # through convex bodywork and leave only its edges visible.
    return mesh(
        name,
        verts,
        [
            (i * 7 + j + 1, i * 7 + j, (i + 1) * 7 + j, (i + 1) * 7 + j + 1)
            for i in range(len(path) - 1)
            for j in range(6)
        ],
        mat,
    )


def rounded_box(name, position, dimensions, mat, bevel=0.02):
    bpy.ops.mesh.primitive_cube_add(size=1, location=V(position))
    obj = bpy.context.object
    obj.scale = (dimensions[0], dimensions[2], dimensions[1])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    register(obj, name, mat)
    if bevel:
        mod = obj.modifiers.new("Edge radii", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod = obj.modifiers.new("Corner normals", "WEIGHTED_NORMAL")
    return obj


def wing(name, halfspan, z0, y0, chord, camber, sweep, mat):
    verts, faces = [], []
    spans, sections = 40, 24
    # Closed airfoil section with a rounded leading edge and thin trailing edge.
    for i in range(spans + 1):
        x = (i / spans * 2 - 1) * halfspan
        u = abs(x / halfspan)
        local_chord = chord * (1 - 0.16 * u * u)
        for j in range(sections):
            theta = j / sections * 2 * PI
            t = (1 - math.cos(theta)) / 2
            thickness = 0.009 * math.sin(theta) * (1 - 0.65 * t)
            y = y0 + camber * math.sin(PI * t) + thickness + 0.035 * u * u
            z = z0 + t * local_chord + sweep * u * u
            verts.append((x, y, z))
    for i in range(spans):
        for j in range(sections):
            a = i * sections + j
            b = i * sections + (j + 1) % sections
            faces.append((a, b, b + sections, a + sections))
    faces += [
        tuple(reversed(range(sections))),
        tuple(spans * sections + j for j in range(sections)),
    ]
    return mesh(name, verts, faces, mat, 1)


def tyre(name, x, z, width, radius, mat):
    profile = [
        (-0.5, 0.69),
        (-0.505, 0.82),
        (-0.48, 0.92),
        (-0.40, 0.985),
        (-0.29, 1),
        (0.29, 1),
        (0.40, 0.985),
        (0.48, 0.92),
        (0.505, 0.82),
        (0.5, 0.69),
    ]
    verts, faces = [], []
    n = 80
    for a, r in profile:
        for j in range(n):
            t = j / n * 2 * PI
            verts.append(
                (
                    x + a * width,
                    radius + math.cos(t) * radius * r,
                    z + math.sin(t) * radius * r,
                )
            )
    for k in range(len(profile) - 1):
        for j in range(n):
            a = k * n + j
            b = k * n + (j + 1) % n
            faces.append((a, b, b + n, a + n))
    return mesh(name, verts, faces, mat, 1)


def ring(name, center, radius, thickness, mat, axis="x"):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=radius,
        minor_radius=thickness,
        major_segments=64,
        minor_segments=8,
        location=V(center),
    )
    obj = bpy.context.object
    if axis == "x":
        obj.rotation_euler[1] = PI / 2
    return register(obj, name, mat)


def build_car(team, params):
    global COMPONENT
    ferrari = team == "ferrari"
    red = material(
        "Rosso paint" if ferrari else "Silver paint",
        (0.62, 0.009, 0.022) if ferrari else (0.43, 0.49, 0.51),
        0.26,
        0.25 if ferrari else 0.7,
        0.38,
    )
    white = material(
        "White upper livery" if ferrari else "Graphite rear livery",
        (0.82, 0.84, 0.83) if ferrari else (0.013, 0.018, 0.019),
        0.27,
        0.15,
        0.35,
    )
    carbon = material(
        "Carbon twill", (0.025, 0.026, 0.03), 0.36, 0.22, texture=weave_texture()
    )
    black = material("Intake darkness", (0.005, 0.006, 0.008), 0.85)
    rubber = material("Slick tyre rubber", (0.005, 0.006, 0.007), 0.86)
    rubber.node_tree.nodes.get("Principled BSDF").inputs[
        "Specular IOR Level"
    ].default_value = 0.22
    alloy = material(
        "Black magnesium wheels and hardware", (0.022, 0.026, 0.030), 0.38, 0.82
    )
    accent = material(
        "Livery pinstripe",
        (0.84, 0.018, 0.025) if ferrari else (0.005, 0.66, 0.51),
        0.28,
        0.25,
        0.25,
    )
    amber = material("Tyre sidewall marking", (0.55, 0.56, 0.53), 0.7)
    lens = material("Rear light lens", (0.8, 0.005, 0.002), 0.2)
    lens.node_tree.nodes.get("Principled BSDF").inputs[
        "Emission Color"
    ].default_value = (0.7, 0.0, 0.0, 1)
    lens.node_tree.nodes.get("Principled BSDF").inputs[
        "Emission Strength"
    ].default_value = 1

    COMPONENT = "chassis"
    body = loft(
        "survival_cell",
        [
            (-1.32, 0.17, 0.36, 0.10),
            (-1.26, 0.20, 0.37, 0.13),
            (-0.93, 0.26, 0.39, 0.18),
            (-0.61, 0.31, 0.40, 0.20),
            (-0.05, 0.335, 0.39, 0.205),
            (0.36, 0.30, 0.38, 0.2),
            (0.49, 0.23, 0.35, 0.14),
            (0.5, 0.21, 0.34, 0.12),
        ],
        red if ferrari else carbon,
    )
    # Actual open cockpit: cut through the top of the shell, keeping its floor.
    bpy.context.view_layer.objects.active = body
    for mod in list(body.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=48, ring_count=24, location=V((0, 0.75, -0.13))
    )
    cutter = bpy.context.object
    cutter.scale = (0.265, 0.53, 0.49)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    boolean = body.modifiers.new("Cockpit aperture", "BOOLEAN")
    boolean.object = cutter
    boolean.operation = "DIFFERENCE"
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.modifier_apply(modifier=boolean.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    loft(
        "seat",
        [
            (-0.49, 0.12, 0.31, 0.045),
            (-0.38, 0.18, 0.28, 0.05),
            (0.07, 0.19, 0.28, 0.05),
            (0.30, 0.15, 0.42, 0.11),
            (0.34, 0.11, 0.45, 0.08),
        ],
        black,
    )
    for side in (-1, 1):
        loft(
            "cockpit_sill_" + str(side),
            [
                (-0.68, 0.035, 0.59, 0.025),
                (-0.46, 0.055, 0.61, 0.036),
                (0.10, 0.045, 0.60, 0.035),
                (0.35, 0.05, 0.60, 0.028),
            ],
            white,
            side * 0.29,
            subdivisions=2,
        )
        rod(
            "mirror_stalk",
            (side * 0.30, 0.57, -0.53),
            (side * 0.61, 0.64, -0.51),
            0.012,
            carbon,
        )
        rounded_box(
            "mirror", (side * 0.63, 0.665, -0.51), (0.17, 0.065, 0.09), red, 0.02
        )
    rounded_box("steering_wheel", (0, 0.48, -0.47), (0.25, 0.08, 0.045), carbon, 0.025)
    rod("telemetry_aerial", (0, 0.58, -0.85), (0, 0.76, -0.85), 0.003, carbon, 8)

    COMPONENT = "nose"
    p = params[COMPONENT]
    nose = loft(
        "impact_structure",
        [
            (-2.37, p["tip_width"] * 0.48, 0.265, 0.045),
            (-2.34, p["tip_width"] * 0.5, 0.28, 0.065),
            (-2.12, 0.09, 0.32, 0.075),
            (-1.65, 0.125, 0.38, 0.10),
            (-1.19, 0.195, p["shoulder_height"] - 0.13, 0.13),
            (-0.86, 0.25, 0.42, 0.17),
            (-0.8, 0.255, 0.42, 0.17),
        ],
        red,
        exponent=0.6,
    )
    for side in (-1, 1):
        loft(
            "wing_pylon",
            [
                (-2.35, 0.014, 0.17, 0.10),
                (-2.27, 0.018, 0.19, 0.12),
                (-2.18, 0.016, 0.24, 0.08),
            ],
            carbon,
            side * 0.058,
            subdivisions=1,
        )
        if not ferrari:
            paint_ribbon(
                "turquoise_nose_line",
                [
                    (side * 0.042, 0.316, -2.31),
                    (side * 0.069, 0.396, -2.09),
                    (side * 0.099, 0.475, -1.66),
                    (side * 0.15, 0.514, -1.19),
                ],
                0.016,
                accent,
                nose,
            )

    COMPONENT = "front_wing"
    p = params[COMPONENT]
    for i in range(3):
        wing(
            ("mainplane", "flap_1", "flap_2")[i],
            0.875 - i * 0.022,
            -2.57 + i * 0.155,
            0.10 + i * 0.056,
            p["chord"] * (1 - i * 0.16),
            p["camber"],
            p["sweep"],
            carbon,
        )
    for side in (-1, 1):
        # Curved endplates follow the wing's outboard contour.
        obj = mesh(
            "endplate",
            [
                (side * 0.878, 0.065, -2.40),
                (side * 0.89, 0.08, -2.10),
                (side * 0.884, 0.30, -2.01),
                (side * 0.875, 0.29, -2.34),
            ],
            [(0, 1, 2, 3)],
            red,
        )
        mod = obj.modifiers.new("Endplate thickness", "SOLIDIFY")
        mod.thickness = 0.009
        mod = obj.modifiers.new("Edge radii", "BEVEL")
        mod.width = 0.018
        mod.segments = 4
        tube(
            "tip_roll",
            [
                (side * 0.84, 0.07, -2.42),
                (side * 0.885, 0.1, -2.3),
                (side * 0.89, 0.095, -2.06),
            ],
            0.015,
            carbon,
        )

    COMPONENT = "sidepods"
    p = params[COMPONENT]
    for side in (-1, 1):
        cx = side * (0.36 + p["width"] * 0.45)
        half = p["width"] * 0.5
        # Open leading rim, separate dark duct with depth; no painted black rectangle.
        shell = loft(
            "shell_" + str(side),
            [
                (-0.48, half, 0.47, p["inlet_height"] * 0.57),
                (-0.43, half * 1.06, 0.47, p["inlet_height"] * 0.61),
                (-0.25, half * 1.10, 0.44, 0.15),
                (0.15, half * 1.06, 0.38, 0.18),
                (0.63, half * 0.95, 0.30, 0.135, side * 0.45),
                (1.12, half * 0.72, 0.24, 0.095, side * 0.32),
                (1.43, half * 0.45, 0.23, 0.065, side * 0.22),
                (1.58, half * 0.22, 0.23, 0.05, side * 0.15),
            ],
            red if ferrari else white,
            offset=cx,
            exponent=0.6,
            cap=False,
        )
        loft(
            "inlet_duct_" + str(side),
            [
                (-0.46, half * 0.92, 0.47, p["inlet_height"] * 0.49),
                (-0.31, half * 0.86, 0.455, p["inlet_height"] * 0.44),
                (-0.18, half * 0.65, 0.42, p["inlet_height"] * 0.32),
            ],
            black,
            offset=cx,
            exponent=0.55,
            cap=False,
            subdivisions=1,
        )
        loft(
            "inlet_shadow_" + str(side),
            [
                (-0.22, half * 0.73, 0.43, p["inlet_height"] * 0.36),
                (-0.18, half * 0.65, 0.42, p["inlet_height"] * 0.32),
            ],
            black,
            offset=cx,
            subdivisions=1,
        )
        tube(
            "inlet_lip",
            [
                (cx - half * 0.83, 0.51, -0.491),
                (cx - half * 0.7, 0.47 + p["inlet_height"] * 0.5, -0.495),
                (cx + half * 0.7, 0.47 + p["inlet_height"] * 0.5, -0.495),
                (cx + half * 0.93, 0.50, -0.488),
            ],
            0.013,
            red,
        )
        paint_ribbon(
            "lower_flow_line",
            [
                (side * 0.70, 0.365, -0.18),
                (side * 0.70, 0.285, 0.20),
                (side * 0.65, 0.205, 0.7),
                (side * 0.51, 0.20, 1.15),
            ],
            0.012,
            accent,
            shell,
        )
        if not ferrari:
            paint_ribbon(
                "upper_turquoise_sweep",
                [
                    (cx + side * half * 0.85, 0.55, -0.48),
                    (side * 0.69, 0.52, -0.24),
                    (side * 0.65, 0.48, 0.15),
                    (side * 0.56, 0.405, 0.55),
                    (side * 0.41, 0.335, 0.95),
                ],
                0.032,
                accent,
                shell,
            )
        # Undercut guide / lower boundary controlled independently of the inlet.
        tube(
            "undercut",
            [
                (side * 0.43, 0.24, -0.34),
                (side * (0.60 - p["undercut"]), 0.18, 0.15),
                (side * 0.40, 0.15, 0.78),
            ],
            0.024,
            carbon,
        )
        for j in range(7):
            z = 0.04 + j * 0.075
            rounded_box(
                "cooling_louvre",
                (side * 0.39, 0.565 - j * 0.019, z),
                (0.105, 0.007, 0.018),
                carbon,
                0.006,
            )

    COMPONENT = "engine_cover"
    p = params[COMPONENT]
    loft(
        "engine_body",
        [
            (0.22, 0.21, 0.45, 0.15),
            (0.34, 0.225, 0.47, 0.18),
            (0.62, 0.22, 0.46, 0.20),
            (1.10, 0.17, 0.37, 0.17),
            (1.56, p["tail_width"], 0.30, 0.13),
            (1.87, 0.06, 0.29, 0.065),
        ],
        red if ferrari else white,
    )
    loft(
        "upper_spine",
        [
            (0.30, 0.065, 0.80, 0.14),
            (0.34, 0.085, 0.81, p["spine_height"] - 0.81),
            (0.47, 0.09, 0.80, 0.15),
            (0.83, 0.06, 0.67, 0.16),
            (1.27, 0.035, 0.52, 0.12),
            (1.65, 0.023, 0.4, 0.07),
        ],
        white,
        exponent=0.7,
    )
    # Airbox mouth with a curved roll structure and recessed throat.
    mouth = (
        [
            (-0.11, 0.73, 0.20),
            (-0.095, 0.91, 0.22),
            (0, p["spine_height"], 0.24),
            (0.095, 0.91, 0.22),
            (0.11, 0.73, 0.20),
            (0, 0.72, 0.20),
        ]
        if ferrari
        else [
            (-0.10, 0.75, 0.20),
            (-0.105, 0.88, 0.20),
            (-0.07, 0.915, 0.20),
            (0.07, 0.915, 0.20),
            (0.105, 0.88, 0.20),
            (0.10, 0.75, 0.20),
            (0.07, 0.73, 0.20),
            (-0.07, 0.73, 0.20),
        ]
    )
    tube("airbox_rim", mouth, 0.015, carbon if ferrari else accent, cyclic=True)
    loft(
        "airbox_throat",
        [(0.18, 0.084, 0.82, 0.09), (0.35, 0.069, 0.81, 0.07)],
        black,
        subdivisions=1,
    )
    rod("camera_support", (0, p["spine_height"], 0.40), (0, 1.04, 0.40), 0.012, carbon)
    rounded_box("onboard_camera", (0, 1.055, 0.40), (0.23, 0.038, 0.065), carbon, 0.014)
    fin = mesh(
        "dorsal_fin",
        [
            (0, 0.85, 0.42),
            (0, 0.79, 0.85),
            (0, 0.53, 1.57),
            (0, 0.37, 1.6),
            (0, 0.48, 0.8),
        ],
        [(0, 1, 2, 3, 4)],
        white,
    )
    mod = fin.modifiers.new("Fin thickness", "SOLIDIFY")
    mod.thickness = 0.009
    rod("exhaust", (0, 0.34, 1.55), (0, 0.37, 2.04), 0.039, alloy, 32)

    COMPONENT = "halo"
    tube(
        "titanium_arch",
        [
            (-0.29, 0.63, 0.20),
            (-0.325, 0.78, -0.02),
            (-0.25, 0.82, -0.47),
            (0, 0.835, -0.66),
            (0.25, 0.82, -0.47),
            (0.325, 0.78, -0.02),
            (0.29, 0.63, 0.20),
        ],
        0.025,
        carbon,
    )
    tube(
        "centre_pillar",
        [(0, 0.52, -0.77), (0, 0.63, -0.73), (0, 0.835, -0.66)],
        0.025,
        carbon,
    )

    COMPONENT = "floor"
    p = params[COMPONENT]
    zvals = [-0.96, -0.88, -0.55, 0.10, 0.75, 1.22, 1.75, 2.0]
    widths = [
        0.37,
        0.58,
        p["edge_width"],
        p["edge_width"],
        p["edge_width"] * 0.93,
        0.63,
        0.54,
        0.51,
    ]
    verts = [(side * w, 0.085, z) for side in (-1, 1) for w, z in zip(widths, zvals)]
    faces = [(i, i + 1, i + 9, i + 8) for i in range(7)]
    obj = mesh("main_surface", verts, faces, carbon)
    mod = obj.modifiers.new("Floor thickness", "SOLIDIFY")
    mod.thickness = 0.015
    mod = obj.modifiers.new("Floor edge bevel", "BEVEL")
    mod.width = 0.008
    mod.segments = 3
    for side in (-1, 1):
        tube(
            "edge_wing",
            [
                (side * p["edge_width"], 0.095, -0.38),
                (side * (p["edge_width"] + 0.005), 0.12, 0.02),
                (side * p["edge_width"] * 0.97, 0.13, 0.53),
                (side * 0.63, 0.14, 1.23),
            ],
            0.012,
            carbon,
        )
        obj = mesh(
            "forward_deflector",
            [
                (side * 0.68, 0.09, -0.87),
                (side * 0.79, 0.10, -0.65),
                (side * 0.74, 0.43, -0.59),
                (side * 0.65, 0.44, -0.79),
            ],
            [(0, 1, 2, 3)],
            carbon,
        )
        mod = obj.modifiers.new("Deflector thickness", "SOLIDIFY")
        mod.thickness = 0.008
    rounded_box(
        "plank",
        (0, 0.055, 0.50),
        (0.22, 0.012, 2.85),
        material("Plank", (0.09, 0.065, 0.035), 0.8),
        0.005,
    )

    COMPONENT = "diffuser"
    p = params[COMPONENT]
    verts = [
        (x, y, z)
        for z, y in (
            (1.12, 0.08),
            (1.48, 0.11),
            (1.83, p["exit_height"] * 0.78),
            (2.15, p["exit_height"]),
        )
        for x in (-0.51, 0.51)
    ]
    obj = mesh(
        "expansion_surface",
        verts,
        [(0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 7, 6)],
        carbon,
        1,
    )
    mod = obj.modifiers.new("Shell thickness", "SOLIDIFY")
    mod.thickness = 0.012
    for x in (-0.5, -0.27, 0, 0.27, 0.5):
        obj = mesh(
            "strake",
            [
                (x, 0.07, 1.22),
                (x, 0.08, 2.16),
                (x, p["exit_height"], 2.16),
                (x, 0.10, 1.22),
            ],
            [(0, 1, 2, 3)],
            carbon,
        )
        mod = obj.modifiers.new("Strake thickness", "SOLIDIFY")
        mod.thickness = 0.008

    COMPONENT = "rear_wing"
    p = params[COMPONENT]
    for i in range(3):
        wing(
            ("mainplane", "flap_1", "flap_2")[i],
            0.505,
            1.86 + i * 0.135,
            0.80 + i * 0.075,
            p["chord"] * (1 - i * 0.16),
            p["camber"],
            -0.055,
            carbon,
        )
    for side in (-1, 1):
        obj = mesh(
            "endplate",
            [
                (side * 0.51, 0.90, 1.83),
                (side * 0.515, 0.92, 2.29),
                (side * 0.515, 0.73, 2.34),
                (side * 0.46, 0.53, 2.12),
                (side * 0.35, 0.28, 1.84),
                (side * 0.42, 0.39, 1.84),
            ],
            [(0, 1, 2, 3, 4, 5)],
            carbon,
        )
        mod = obj.modifiers.new("Endplate skin", "SOLIDIFY")
        mod.thickness = 0.012
        mod = obj.modifiers.new("Curved edges", "BEVEL")
        mod.width = 0.035
        mod.segments = 5
        tube(
            "mount",
            [
                (side * 0.12, 0.30, 1.7),
                (side * 0.13, 0.58, 1.82),
                (side * 0.13, 0.82, 2.0),
            ],
            0.019,
            carbon,
        )
        rounded_box(
            "led_strip", (side * 0.513, 0.80, 2.32), (0.015, 0.145, 0.012), lens, 0.005
        )
    rounded_box("rear_rain_light", (0, 0.32, 2.11), (0.075, 0.065, 0.025), lens, 0.009)

    COMPONENT = "suspension"
    for axle, z in (("front", -1.7), ("rear", 1.7)):
        for side in (-1, 1):
            x = side * (0.81 if axle == "front" else 0.76)
            for h in (0.22, 0.44):
                for dz in (-0.27, 0.23):
                    rod(
                        axle + "_wishbone",
                        (side * 0.21, h + 0.02, z + dz),
                        (x, h, z),
                        0.012,
                        carbon,
                    )
            rod(
                axle + "_pushrod",
                (side * 0.20, 0.52, z + 0.12),
                (x, 0.22, z),
                0.014,
                carbon,
            )
            rod(
                axle + "_trackrod",
                (side * 0.20, 0.31, z - 0.10),
                (x, 0.32, z - 0.06),
                0.008,
                alloy,
            )
            rounded_box(
                axle + "_brake_duct",
                (x - side * 0.09, 0.36, z),
                (0.07, 0.14, 0.19),
                carbon,
                0.035,
            )
            rod(axle + "_axle", (side * 0.20, 0.352, z), (x, 0.352, z), 0.017, alloy)

    COMPONENT = "wheels"
    for tag, x, z, width, radius in (
        ("fl", -0.81, -1.7, 0.28, 0.352),
        ("fr", 0.81, -1.7, 0.28, 0.352),
        ("rl", -0.76, 1.7, 0.375, 0.355),
        ("rr", 0.76, 1.7, 0.375, 0.355),
    ):
        tyre(tag + "_tyre", x, z, width, radius, rubber)
        side = 1 if x > 0 else -1
        outer = x + side * (width * 0.48)
        rod(
            tag + "_rim_barrel",
            (x - width * 0.46, radius, z),
            (x + width * 0.46, radius, z),
            0.229,
            alloy,
            64,
        )
        # Dark inset dish masks the solid barrel and provides a convincing rim cavity.
        rod(
            tag + "_rim_inset",
            (outer, radius, z),
            (outer + side * 0.004, radius, z),
            0.213,
            black,
            64,
        )
        ring(tag + "_rim_lip", (outer + side * 0.005, radius, z), 0.22, 0.008, alloy)
        ring(
            tag + "_sidewall_line",
            (outer + side * 0.005, radius, z),
            0.284,
            0.0025,
            amber,
        )
        for j in range(10):
            a = j * 2 * PI / 10
            rod(
                tag + "_spoke",
                (
                    outer + side * 0.009,
                    radius + math.sin(a) * 0.065,
                    z + math.cos(a) * 0.065,
                ),
                (
                    outer + side * 0.010,
                    radius + math.sin(a + 0.09) * 0.203,
                    z + math.cos(a + 0.09) * 0.203,
                ),
                0.010,
                alloy,
            )
        rod(
            tag + "_hub",
            (outer, radius, z),
            (outer + side * 0.024, radius, z),
            0.048,
            alloy,
            24,
        )
        rod(
            tag + "_centre_lock",
            (outer + side * 0.022, radius, z),
            (outer + side * 0.030, radius, z),
            0.025,
            accent,
            6,
        )

    # Put origins at each component's anchor without moving its geometry.
    catalog = json.loads((Path(__file__).parent / "catalog.json").read_text())
    for obj in CAR_OBJECTS:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        if obj.type == "CURVE":
            bpy.ops.object.convert(target="MESH")
        uv_project(obj)
        bpy.context.scene.cursor.location = V(
            catalog["components"][obj["component"]]["anchor"]
        )
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")


def studio():
    world = bpy.context.scene.world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.15,
        0.17,
        0.2,
        1,
    )
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.18
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.012))
    floor = bpy.context.object
    floor.name = "Studio ground"
    floor.data.materials.append(
        material("Studio graphite", (0.022, 0.027, 0.034), 0.48, 0.12)
    )
    for name, pos, power, size, color in (
        ("Key softbox", (2.8, 5, -1.2), 950, 5, (1, 0.95, 0.9)),
        ("Roof strip", (-1.8, 4.2, 0.3), 600, 4, (0.83, 0.9, 1)),
        ("Rear separation", (0.8, 2.8, 4.3), 650, 3, (0.9, 0.96, 1)),
        ("Front fill", (0, 1.8, -4), 220, 2.5, (1, 1, 1)),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = power
        data.shape = "RECTANGLE"
        data.size = size
        data.size_y = size * 0.4
        data.color = color
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = V(pos)
        obj.rotation_euler = (
            (V((0, 0.3, 0)) - obj.location).to_track_quat("-Z", "Y").to_euler()
        )
    data = bpy.data.cameras.new("Studio camera")
    camera = bpy.data.objects.new("Studio camera", data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera
    return camera


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--preview-only", action="store_true")
    parser.add_argument("--geometry-only", action="store_true")
    parser.add_argument("--samples", type=int, default=64)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    spec = json.loads(Path(args.input).read_text())
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system = "METRIC"
    build_car(spec["team_key"], spec["parameters"])
    bpy.ops.object.select_all(action="DESELECT")
    for obj in CAR_OBJECTS:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(out / "car.glb"),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_extras=True,
        export_yup=True,
    )
    # Component mesh hashes are independent of GLB serialization and other components.
    hashes = {}
    material_hashes = {}
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        signature = {"name": mat.name, "inputs": {}, "images": []}
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            for key in (
                "Base Color",
                "Roughness",
                "Metallic",
                "Coat Weight",
                "Specular IOR Level",
            ):
                value = bsdf.inputs[key].default_value
                signature["inputs"][key] = (
                    list(value) if hasattr(value, "__len__") else value
                )
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                signature["images"].append(
                    hashlib.sha256(
                        np.array(node.image.pixels[:], dtype=np.float32).tobytes()
                    ).hexdigest()
                )
        material_hashes[mat.name] = json.dumps(
            signature, sort_keys=True, separators=(",", ":")
        )
    deps = bpy.context.evaluated_depsgraph_get()
    for component in sorted({o["component"] for o in CAR_OBJECTS}):
        h = hashlib.sha256()
        for obj in sorted(
            (o for o in CAR_OBJECTS if o["component"] == component),
            key=lambda o: o.name,
        ):
            evaluated = obj.evaluated_get(deps)
            data = evaluated.to_mesh()
            # Boolean evaluation may reorder vertices between Blender processes.
            # Canonical polygon positions describe shape independently of buffer order.
            positions = [
                tuple(round(c, 6) for c in obj.matrix_world @ v.co)
                for v in data.vertices
            ]
            polygons = sorted(
                tuple(sorted(positions[index] for index in polygon.vertices))
                for polygon in data.polygons
            )
            h.update(json.dumps(polygons, separators=(",", ":")).encode())
            for mat in data.materials:
                h.update(material_hashes.get(mat.name, mat.name).encode())
            evaluated.to_mesh_clear()
        hashes[component] = h.hexdigest()
    (out / "geometry.json").write_text(
        json.dumps(
            {"component_hashes": hashes, "generator_version": "2026.1"}, indent=2
        )
    )
    camera = studio()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    import _cycles

    # Debian ARM64 does not ship OpenImageDenoise; do not request an absent kernel.
    scene.cycles.use_denoising = (
        getattr(_cycles, "with_openimagedenoise", False) is True
    )
    scene.cycles.seed = 17
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 0
    scene.cycles.adaptive_threshold = 0.035
    scene.cycles.adaptive_min_samples = 16
    scene.cycles.sample_clamp_indirect = 2
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    views = {
        "three_quarter": (5, 2.6, -7),
        "front": (0, 1.15, -8),
        "side": (8, 1.15, 0),
        "rear": (0, 1.25, 8),
    }
    camera.data.lens = 52
    for view, pos in views.items():
        camera.location = V(pos)
        camera.rotation_euler = (
            (V((0, 0.35, 0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
        )
        if view == "three_quarter":
            bpy.ops.wm.save_as_mainfile(filepath=str(out / "source.blend"))
        if args.geometry_only:
            continue
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(out / ("preview_" + view + ".png"))
        bpy.ops.render.render(write_still=True)
        if not args.preview_only:
            scene.render.resolution_x = 3840
            scene.render.resolution_y = 2160
            scene.render.filepath = str(out / ("render_" + view + ".png"))
            bpy.ops.render.render(write_still=True)
    print("F1_BUILD_COMPLETE", flush=True)


if __name__ == "__main__":
    main()

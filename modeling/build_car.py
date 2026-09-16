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
ATTACHMENTS = []


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


def body_attachment(surface, side, height, z):
    """Seat the inboard joint inside the evaluated shell, including subdivision.

    These are exterior reconstruction mounts, not factory suspension hardpoints.
    Searching the actual shell avoids floating arms when the nose taper changes.
    """
    bpy.context.view_layer.update()
    tree = BVHTree.FromObject(surface, bpy.context.evaluated_depsgraph_get())
    hit, normal, _, _ = tree.find_nearest(V((side * 0.24, height, z)))
    point = hit - normal * 0.004
    anchor = (point.x, point.z, -point.y)
    ATTACHMENTS.append({"surface": surface.name, "anchor": anchor})
    return anchor


def suspension_blade(name, a, b, mat):
    """Closed lenticular fairing, with its chord along the airflow."""
    a, b = Vector(a), Vector(b)
    axis = (b - a).normalized()
    chord = Vector((0, 0, 1))
    chord = (chord - axis * chord.dot(axis)).normalized()
    thickness = axis.cross(chord).normalized()
    vertices = []
    for t, scale in ((0, 0.7), (0.04, 1), (0.85, 1), (1, 0.7)):
        centre = a.lerp(b, t)
        for j in range(16):
            angle = 2 * PI * j / 16
            vertices.append(
                tuple(
                    centre
                    + chord * (0.031 * scale * math.cos(angle))
                    + thickness * (0.009 * math.sin(angle))
                )
            )
    faces = [
        (
            i * 16 + j,
            i * 16 + (j + 1) % 16,
            (i + 1) * 16 + (j + 1) % 16,
            (i + 1) * 16 + j,
        )
        for i in range(3)
        for j in range(16)
    ]
    faces.extend([tuple(reversed(range(16))), tuple(range(48, 64))])
    return mesh(name, vertices, faces, mat)


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


def pod_surface(name, sections, side, mat, channel=0):
    """Asymmetric sections: z, inner x, outer x, roof y, belly y.

    The shoulder stays wide while the belly tucks inward. Unlike a symmetric
    ellipse this creates a real overhang and undercut in the side silhouette.
    Section stations are authored estimates from the dated launch photographs.
    """
    verts, faces = [], []
    for z, inner, outer, roof, belly in sections:
        w, h = outer - inner, roof - belly
        depression = channel * min(1, max(0, (z + 0.3) / 0.5))
        outline = [
            (inner, roof - h * 0.12 - depression * 0.6),
            (inner + w * 0.25, roof - depression),
            (outer - w * 0.16, roof),
            (outer, roof - h * 0.12),
            (outer, roof - h * 0.34),
            (outer - w * 0.08, belly + h * 0.22),
            (outer - w * 0.28, belly),
            (inner + w * 0.12, belly),
            (inner, belly + h * 0.18),
        ]
        verts.extend((side * x, y, z) for x, y in outline)
    n = 9
    for i in range(len(sections) - 1):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            face = (a, b, b + n, a + n)
            faces.append(tuple(reversed(face)) if side > 0 else face)
    return mesh(name, verts, faces, mat, 2)


def intake(name, outline, depth, rim_mat, dark_mat):
    """Open rim, recessed walls and back face; no solid plug at the mouth."""
    tube(name + "_rim", outline, 0.008, rim_mat, cyclic=True)
    center = sum((Vector(p) for p in outline), Vector()) / len(outline)
    back = [
        (center.x + (x - center.x) * 0.70, center.y + (y - center.y) * 0.70, z + depth)
        for x, y, z in outline
    ]
    n = len(outline)
    obj = mesh(
        name + "_duct",
        outline + back,
        [(j, (j + 1) % n, (j + 1) % n + n, j + n) for j in range(n)]
        + [tuple(range(n, n * 2))],
        dark_mat,
    )
    # Duct walls are visible from the opening as well as around the throat.
    obj.data.materials[0].use_backface_culling = False
    return obj


def front_boundary(surface, z):
    """Use the evaluated body edge for the inlet: no disconnected guessed rim."""
    bpy.context.view_layer.update()
    evaluated = surface.evaluated_get(bpy.context.evaluated_depsgraph_get())
    data = evaluated.to_mesh()
    points = [
        (v.co.x, v.co.z, -v.co.y) for v in data.vertices if abs(-v.co.y - z) < 0.00001
    ]
    evaluated.to_mesh_clear()
    if len(points) < 8:
        raise ValueError("Could not resolve the sidepod opening boundary.")
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return sorted(points, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))


def intake_cowl(outline, mat):
    """Continuous outer fairing around the open airbox throat."""
    cx = sum(p[0] for p in outline) / len(outline)
    cy = sum(p[1] for p in outline) / len(outline)
    verts, faces = [], []
    n = len(outline)
    for dz, scale in ((0, 1.06), (0.025, 1.08), (0.19, 1.13), (0.28, 1.14)):
        verts.extend(
            (cx + (x - cx) * scale, cy + (y - cy) * scale, z + dz)
            for x, y, z in outline
        )
    for i in range(3):
        faces.extend(
            (i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j)
            for j in range(n)
        )
    return mesh("airbox_outer_cowl", verts, faces, mat, 2)


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


def station_sample(rows, value):
    """Shape-preserving cubic interpolation of editable silhouette stations.

    Each row starts with its coordinate; remaining columns are independent
    dimensions. Harmonic tangents avoid overshooting small gaps or thin lips.
    These are visual estimates, not measured factory sections.
    """
    xs = np.array([r[0] for r in rows])
    ys = np.array([r[1:] for r in rows], dtype=float)
    slopes = np.diff(ys, axis=0) / np.diff(xs)[:, None]
    tangents = np.zeros_like(ys)
    tangents[0], tangents[-1] = slopes[0], slopes[-1]
    for i in range(1, len(rows) - 1):
        for j in range(ys.shape[1]):
            a, b = slopes[i - 1, j], slopes[i, j]
            if a * b > 0:
                tangents[i, j] = 2 * a * b / (a + b)
    k = min(max(int(np.searchsorted(xs, value)) - 1, 0), len(xs) - 2)
    h = xs[k + 1] - xs[k]
    t = min(1, max(0, (value - xs[k]) / h))
    return (
        (2 * t**3 - 3 * t**2 + 1) * ys[k]
        + (t**3 - 2 * t * t + t) * h * tangents[k]
        + (-2 * t**3 + 3 * t * t) * ys[k + 1]
        + (t**3 - t * t) * h * tangents[k + 1]
    )


def sectional_wing(name, stations, mat, *, split=False):
    """Closed airfoil skin: x, leading Z/Y, chord, trailing rise, camber, thickness.

    Planform, spanwise droop and twist are authored separately for each element.
    Upper front flaps terminate at the nose instead of passing through it.
    """
    for side in (-1, 1) if split else (0,):
        verts, faces = [], []
        spans, sections = (36 if split else 72), 32
        for i in range(spans + 1):
            if side:
                x = side * (
                    stations[0][0] + (stations[-1][0] - stations[0][0]) * i / spans
                )
            else:
                x = stations[-1][0] * (2 * i / spans - 1)
            z, y, chord, rise, camber, thickness = station_sample(stations, abs(x))
            for j in range(sections):
                theta = 2 * PI * j / sections
                t = (1 - math.cos(theta)) / 2
                skin = thickness * math.sin(theta) * (1 - 0.72 * t)
                verts.append(
                    (x, y + rise * t + camber * math.sin(PI * t) + skin, z + chord * t)
                )
        for i in range(spans):
            for j in range(sections):
                a, b = i * sections + j, i * sections + (j + 1) % sections
                faces.append((a, b, b + sections, a + sections))
        faces += [
            tuple(reversed(range(sections))),
            tuple(spans * sections + j for j in range(sections)),
        ]
        # Mirrored half surfaces need their winding reversed as well.
        if side == -1:
            faces = [tuple(reversed(f)) for f in faces]
        mesh(
            name + ("_left" if side == -1 else "_right" if side else ""),
            verts,
            faces,
            mat,
        )


def ruled_skin(name, rows, mat, thickness=0.005):
    """Curved thin shell between two 3D rails, with rounded solid edges."""
    verts, faces = [], []
    for i in range(49):
        a = station_sample(rows, rows[0][0] + (rows[-1][0] - rows[0][0]) * i / 48)
        for j in range(5):
            t = j / 4
            verts.append(tuple((1 - t) * a[:3] + t * a[3:]))
    for i in range(48):
        for j in range(4):
            a = i * 5 + j
            faces.append((a, a + 1, a + 6, a + 5))
    obj = mesh(name, verts, faces, mat)
    mod = obj.modifiers.new("Composite skin", "SOLIDIFY")
    mod.thickness = thickness
    mod = obj.modifiers.new("Rounded laminate edges", "BEVEL")
    mod.width, mod.segments = thickness * 0.4, 2
    return obj


def build_front_wing(team, p, carbon, paint):
    # See docs/aero-reconstruction.md: launch orthographic views establish
    # planform; September imagery is a cross-check, not a launch upgrade claim.
    ferrari = team == "ferrari"
    if ferrari:
        main = [
            [0, -2.555, 0.095, 0.20, 0.034, 0.018, 0.007],
            [0.16, -2.55, 0.098, 0.21, 0.038, 0.020, 0.007],
            [0.43, -2.505, 0.125, 0.21, 0.038, 0.019, 0.007],
            [0.69, -2.43, 0.143, 0.195, 0.025, 0.016, 0.006],
            [0.80, -2.41, 0.090, 0.19, 0.018, 0.012, 0.005],
            [0.90, -2.40, 0.114, 0.17, 0.009, 0.009, 0.004],
        ]
        flap = [
            [0.135, -2.365, 0.147, 0.165, 0.058, 0.022, 0.006],
            [0.35, -2.34, 0.168, 0.174, 0.068, 0.024, 0.006],
            [0.61, -2.275, 0.187, 0.16, 0.072, 0.025, 0.006],
            [0.765, -2.255, 0.17, 0.112, 0.055, 0.018, 0.005],
            [0.80, -2.25, 0.158, 0.095, 0.040, 0.014, 0.004],
        ]
        upper = [
            [0.14, -2.225, 0.213, 0.13, 0.064, 0.022, 0.005],
            [0.34, -2.19, 0.246, 0.148, 0.075, 0.027, 0.005],
            [0.59, -2.135, 0.265, 0.14, 0.076, 0.025, 0.005],
            [0.76, -2.16, 0.227, 0.097, 0.050, 0.018, 0.004],
            [0.80, -2.17, 0.205, 0.075, 0.038, 0.012, 0.004],
        ]
        end = [
            [0, 0.812, 0.102, -2.415, 0.802, 0.155, -2.415],
            [0.18, 0.815, 0.095, -2.36, 0.799, 0.252, -2.36],
            [0.48, 0.821, 0.105, -2.25, 0.806, 0.325, -2.25],
            [0.78, 0.824, 0.12, -2.12, 0.812, 0.323, -2.12],
            [1, 0.829, 0.12, -2.025, 0.824, 0.296, -2.025],
        ]
    else:
        main = [
            [0, -2.55, 0.092, 0.195, 0.027, 0.017, 0.007],
            [0.15, -2.54, 0.097, 0.20, 0.033, 0.018, 0.007],
            [0.42, -2.48, 0.12, 0.19, 0.033, 0.017, 0.006],
            [0.67, -2.405, 0.118, 0.175, 0.029, 0.016, 0.006],
            [0.79, -2.395, 0.078, 0.19, 0.023, 0.015, 0.005],
            [0.865, -2.38, 0.136, 0.175, 0.012, 0.013, 0.004],
            [0.90, -2.37, 0.105, 0.16, 0.009, 0.009, 0.004],
        ]
        flap = [
            [0.125, -2.363, 0.14, 0.16, 0.054, 0.022, 0.006],
            [0.32, -2.326, 0.153, 0.15, 0.065, 0.020, 0.006],
            [0.55, -2.27, 0.163, 0.132, 0.070, 0.020, 0.005],
            [0.74, -2.25, 0.156, 0.108, 0.046, 0.018, 0.005],
            [0.80, -2.24, 0.148, 0.086, 0.032, 0.012, 0.004],
        ]
        upper = [
            [0.13, -2.225, 0.204, 0.137, 0.075, 0.023, 0.005],
            [0.34, -2.194, 0.227, 0.124, 0.072, 0.022, 0.005],
            [0.54, -2.16, 0.236, 0.114, 0.062, 0.022, 0.005],
            [0.73, -2.17, 0.20, 0.086, 0.037, 0.013, 0.004],
            [0.80, -2.17, 0.183, 0.067, 0.023, 0.011, 0.004],
        ]
        end = [
            [0, 0.806, 0.082, -2.40, 0.802, 0.147, -2.40],
            [0.2, 0.81, 0.09, -2.345, 0.795, 0.265, -2.345],
            [0.47, 0.816, 0.106, -2.25, 0.797, 0.30, -2.25],
            [0.68, 0.822, 0.122, -2.15, 0.804, 0.287, -2.15],
            [1, 0.83, 0.125, -2.02, 0.819, 0.313, -2.02],
        ]
    chord_scale = p["chord"] / (0.31 if ferrari else 0.285)
    camber_scale = p["camber"] / (0.046 if ferrari else 0.038)
    sweep_delta = p["sweep"] - (0.12 if ferrari else 0.085)
    for name, rows in (("mainplane", main), ("slot_flap", flap), ("upper_flap", upper)):
        adjusted = [
            [
                x,
                z + sweep_delta * (x / 0.9) ** 2,
                y,
                c * chord_scale,
                rise,
                camber * camber_scale,
                thick,
            ]
            for x, z, y, c, rise, camber, thick in rows
        ]
        sectional_wing(name, adjusted, carbon, split=name != "mainplane")
    for side in (-1, 1):
        ruled_skin(
            "endplate",
            [[t, side * x, y, z, side * a, b, c] for t, x, y, z, a, b, c in end],
            carbon,
        )
        # Outboard foot is a swept laminate surface, not a cylindrical tip roll.
        ruled_skin(
            "outboard_foot",
            [
                [0, side * 0.822, 0.10, -2.39, side * 0.90, 0.12, -2.38],
                [
                    0.35,
                    side * 0.83,
                    0.10,
                    -2.27,
                    side * 0.905,
                    0.127 if ferrari else 0.148,
                    -2.26,
                ],
                [0.72, side * 0.834, 0.12, -2.12, side * 0.90, 0.135, -2.10],
                [1, side * 0.836, 0.12, -2.02, side * 0.888, 0.137, -2.005],
            ],
            carbon,
            0.004,
        )
        # Visible slot separators; spacing and mounting sections are estimated.
        for x in (0.21, 0.71):
            for a, b in ((flap, upper),):
                az, ay, ac, ar, *_ = station_sample(a, x)
                bz, by, *_ = station_sample(b, x)
                ruled_skin(
                    "slot_separator",
                    [
                        [
                            0,
                            side * (x - 0.002),
                            ay + ar,
                            az + ac,
                            side * (x + 0.002),
                            ay + ar,
                            az + ac,
                        ],
                        [
                            1,
                            side * (x - 0.002),
                            by + 0.01,
                            bz + 0.018,
                            side * (x + 0.002),
                            by + 0.01,
                            bz + 0.018,
                        ],
                    ],
                    carbon,
                    0.003,
                )


def build_floor(team, p, carbon):
    ferrari = team == "ferrari"
    w = p["edge_width"]
    # z, width, edge height. The central/hidden underside remains approximate.
    outline = (
        [
            [-0.96, 0.37, 0.09],
            [-0.87, 0.67, 0.135],
            [-0.67, w, 0.16],
            [-0.30, w, 0.123],
            [0.15, w - 0.012, 0.103],
            [0.70, w - 0.045, 0.11],
            [1.12, 0.66, 0.13],
            [1.45, 0.57, 0.10],
            [2, 0.51, 0.09],
        ]
        if ferrari
        else [
            [-0.96, 0.37, 0.09],
            [-0.88, 0.70, 0.145],
            [-0.63, w, 0.175],
            [-0.25, w - 0.009, 0.14],
            [0.20, w - 0.026, 0.12],
            [0.68, w - 0.04, 0.14],
            [1.08, 0.68, 0.152],
            [1.46, 0.56, 0.105],
            [2, 0.51, 0.09],
        ]
    )
    verts, faces = [], []
    for i in range(81):
        z = -0.96 + 2.96 * i / 80
        width, height = station_sample(outline, z)
        for j in range(25):
            u = 2 * j / 24 - 1
            verts.append((u * width, 0.085 + (height - 0.085) * abs(u) ** 3, z))
    for i in range(80):
        for j in range(24):
            a = i * 25 + j
            faces.append((a, a + 1, a + 26, a + 25))
    obj = mesh("contoured_upper_surface", verts, faces, carbon)
    mod = obj.modifiers.new("Floor laminate", "SOLIDIFY")
    mod.thickness = 0.009
    for side in (-1, 1):
        lip = []
        for i, z in enumerate((-0.46, -0.26, 0.04, 0.38, 0.72, 1.02, 1.20)):
            width, height = station_sample(outline, z)
            lift = (
                (0.022, 0.034, 0.025, 0.022, 0.029, 0.022, 0.008)[i]
                if ferrari
                else (0.025, 0.042, 0.025, 0.038, 0.043, 0.028, 0.008)[i]
            )
            lip.append(
                [
                    z,
                    side * (width - 0.033),
                    height + 0.016,
                    z,
                    side * (width + 0.008),
                    height + lift + 0.009,
                    z,
                ]
            )
        ruled_skin("sculpted_edge_lip", lip, carbon, 0.004)
        # Separate laminates leave an actual open slot. Small bridges carry
        # the edge element; their dimensions are reconstruction estimates.
        for z in (-0.24, 0.40, 0.98):
            width, height = station_sample(outline, z)
            ruled_skin(
                "edge_slot_bridge",
                [
                    [
                        0,
                        side * (width - 0.045),
                        height - 0.002,
                        z - 0.009,
                        side * (width - 0.045),
                        height - 0.002,
                        z + 0.009,
                    ],
                    [
                        1,
                        side * (width - 0.015),
                        height + 0.035,
                        z - 0.009,
                        side * (width - 0.015),
                        height + 0.035,
                        z + 0.009,
                    ],
                ],
                carbon,
                0.003,
            )
        # S-curved board with swept upper rail, independently authored per team.
        board = (
            [
                [0, 0.65, 0.11, -0.88, 0.62, 0.32, -0.84],
                [0.2, 0.72, 0.135, -0.82, 0.66, 0.43, -0.76],
                [0.55, 0.77, 0.155, -0.70, 0.73, 0.42, -0.65],
                [1, 0.775, 0.145, -0.51, 0.78, 0.27, -0.50],
            ]
            if ferrari
            else [
                [0, 0.67, 0.12, -0.89, 0.64, 0.31, -0.88],
                [0.2, 0.73, 0.15, -0.82, 0.685, 0.41, -0.79],
                [0.55, 0.76, 0.168, -0.67, 0.745, 0.365, -0.66],
                [1, 0.76, 0.15, -0.47, 0.78, 0.23, -0.46],
            ]
        )
        ruled_skin(
            "swept_floor_board",
            [[t, side * x, y, z, side * a, b, c] for t, x, y, z, a, b, c in board],
            carbon,
            0.005,
        )
        ruled_skin(
            "board_lower_turning_surface",
            [
                [0, side * 0.53, 0.135, -0.86, side * 0.66, 0.15, -0.89],
                [
                    0.45,
                    side * 0.60,
                    0.175,
                    -0.70,
                    side * 0.755,
                    0.205 if ferrari else 0.23,
                    -0.70,
                ],
                [1, side * 0.65, 0.13, -0.52, side * 0.77, 0.16, -0.49],
            ],
            carbon,
            0.004,
        )


def build_rear_wing(team, p, carbon):
    ferrari = team == "ferrari"
    profiles = (
        [
            [
                [0, 1.84, 0.79, 0.235, 0.048, 0.023, 0.008],
                [0.22, 1.845, 0.803, 0.23, 0.05, 0.025, 0.008],
                [0.42, 1.84, 0.85, 0.22, 0.038, 0.02, 0.007],
                [0.505, 1.83, 0.866, 0.21, 0.028, 0.018, 0.006],
            ],
            [
                [0, 2.04, 0.843, 0.13, 0.047, 0.02, 0.006],
                [0.25, 2.042, 0.857, 0.13, 0.045, 0.02, 0.006],
                [0.43, 2.03, 0.896, 0.12, 0.033, 0.017, 0.005],
                [0.505, 2.022, 0.90, 0.108, 0.026, 0.014, 0.004],
            ],
            [
                [0, 2.155, 0.902, 0.125, 0.055, 0.02, 0.005],
                [0.24, 2.15, 0.914, 0.125, 0.052, 0.02, 0.005],
                [0.43, 2.13, 0.932, 0.125, 0.039, 0.016, 0.004],
                [0.505, 2.112, 0.933, 0.12, 0.03, 0.014, 0.004],
            ],
        ]
        if ferrari
        else [
            [
                [0, 1.85, 0.817, 0.215, 0.03, 0.019, 0.008],
                [0.27, 1.852, 0.82, 0.21, 0.032, 0.019, 0.008],
                [0.44, 1.848, 0.842, 0.20, 0.022, 0.018, 0.007],
                [0.505, 1.84, 0.852, 0.195, 0.018, 0.015, 0.006],
            ],
            [
                [0, 2.042, 0.854, 0.115, 0.035, 0.017, 0.006],
                [0.27, 2.04, 0.858, 0.115, 0.034, 0.017, 0.006],
                [0.44, 2.033, 0.873, 0.11, 0.028, 0.015, 0.005],
                [0.505, 2.025, 0.879, 0.105, 0.024, 0.012, 0.004],
            ],
            [
                [0, 2.142, 0.903, 0.13, 0.034, 0.019, 0.005],
                [0.27, 2.14, 0.905, 0.13, 0.033, 0.019, 0.005],
                [0.44, 2.13, 0.916, 0.128, 0.029, 0.016, 0.004],
                [0.505, 2.12, 0.92, 0.123, 0.025, 0.014, 0.004],
            ],
        ]
    )
    scaled_profiles = []
    for name, rows in zip(("spoon_mainplane", "slot_flap", "upper_flap"), profiles):
        scaled_profiles.append(
            [
                [
                    x,
                    z,
                    y,
                    c * p["chord"] / (0.31 if ferrari else 0.285),
                    r,
                    k * p["camber"] / (0.052 if ferrari else 0.044),
                    t,
                ]
                for x, z, y, c, r, k, t in rows
            ]
        )
        sectional_wing(
            name,
            [
                [
                    x,
                    z,
                    y,
                    c * p["chord"] / (0.31 if ferrari else 0.285),
                    r,
                    k * p["camber"] / (0.052 if ferrari else 0.044),
                    t,
                ]
                for x, z, y, c, r, k, t in rows
            ],
            carbon,
        )
    # Thin slot separators and exposed hinge barrels. Derive their ends from
    # the same airfoil sections so changes of chord cannot leave loose pieces.
    for x in (-0.44, 0.44):
        for lower, upper in zip(scaled_profiles, scaled_profiles[1:]):
            z, y, chord, rise, camber, _ = station_sample(lower, abs(x))
            a = (x, y + rise * 0.92 + camber * math.sin(PI * 0.92), z + chord * 0.92)
            z, y, chord, rise, camber, _ = station_sample(upper, abs(x))
            b = (x, y + rise * 0.12 + camber * math.sin(PI * 0.12), z + chord * 0.12)
            ruled_skin(
                "slot_separator",
                [
                    [0, x, a[1] - 0.004, a[2] - 0.012, x, a[1] - 0.004, a[2] + 0.012],
                    [1, x, b[1] + 0.004, b[2] - 0.012, x, b[1] + 0.004, b[2] + 0.012],
                ],
                carbon,
                0.003,
            )
            rod(
                "flap_hinge",
                (x - 0.009, b[1], b[2]),
                (x + 0.009, b[1], b[2]),
                0.007,
                carbon,
                16,
            )
    for side in (-1, 1):
        ruled_skin(
            "curved_endplate",
            [
                [0, side * 0.35, 0.29, 1.84, side * 0.385, 0.32, 1.96],
                [
                    0.3,
                    side * (0.425 if ferrari else 0.40),
                    0.50,
                    1.86,
                    side * 0.46,
                    0.53,
                    2.17,
                ],
                [0.58, side * 0.497, 0.70, 1.85, side * 0.514, 0.72, 2.32],
                [0.78, side * 0.51, 0.86, 1.83, side * 0.515, 0.865, 2.31],
                [
                    1,
                    side * 0.507,
                    0.978 if ferrari else 0.96,
                    1.835,
                    side * 0.515,
                    0.98 if ferrari else 0.96,
                    2.28,
                ],
            ],
            carbon,
            0.007,
        )
        z0, y0, chord, rise, camber, _ = station_sample(scaled_profiles[0], 0.13)
        # Follow the underside of each team's mainplane; the old fixed .83 m
        # top left a visible gap under the higher Mercedes wing.
        top = [
            (y0 + rise * t + camber * math.sin(PI * t), z0 + chord * t)
            for t in (0.48, 0.87)
        ]
        ruled_skin(
            "pylon",
            [
                [0, side * 0.12, 0.30, 1.69, side * 0.12, 0.30, 1.79],
                [0.5, side * 0.125, 0.57, 1.79, side * 0.125, 0.57, 1.90],
                [
                    1,
                    side * 0.13,
                    top[0][0],
                    top[0][1],
                    side * 0.13,
                    top[1][0],
                    top[1][1],
                ],
            ],
            carbon,
            0.012,
        )


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
    # A visible dark inner tub follows the aperture. The old seat was below the
    # Boolean bowl, so the cockpit read as a solid painted plate in the viewer.
    verts, faces = [], []
    for width, length, y in (
        (0.235, 0.44, 0.585),
        (0.19, 0.35, 0.43),
        (0.13, 0.27, 0.405),
    ):
        for j in range(48):
            angle = j * 2 * PI / 48
            verts.append((width * math.cos(angle), y, -0.12 + length * math.sin(angle)))
    for i in range(2):
        for j in range(48):
            a, b = i * 48 + j, i * 48 + (j + 1) % 48
            faces.append((a, b, b + 48, a + 48))
    faces.append(tuple(range(96, 144)))
    mesh("cockpit_inner_tub", verts, faces, black, 1)
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
            (-2.12, 0.095 if ferrari else 0.075, 0.32, 0.065),
            (-1.65, 0.145 if ferrari else 0.105, 0.38, 0.085),
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
    build_front_wing(team, p, carbon, red)

    COMPONENT = "sidepods"
    p = params[COMPONENT]
    for side in (-1, 1):
        # Separate station layouts, not a common body scaled about the origin.
        # SF-26: broad forward opening, full shoulder and later coke-bottle taper.
        # W17 launch renders: shallow high slot, relatively flat deck and rear upsweep.
        width_delta = p["width"] - (0.36 if ferrari else 0.315)
        stations = (
            [
                (-0.50, 0.32, 0.74, 0.605, 0.355),
                (-0.47, 0.32, 0.75, 0.605, 0.35),
                (-0.26, 0.32, 0.775, 0.595, 0.265),
                (0.16, 0.30, 0.77, 0.565, 0.225),
                (0.58, 0.27, 0.69, 0.50, 0.205),
                (0.98, 0.23, 0.56, 0.41, 0.19),
                (1.34, 0.17, 0.36, 0.325, 0.185),
                (1.63, 0.105, 0.20, 0.285, 0.19),
            ]
            if ferrari
            else [
                (-0.51, 0.32, 0.715, 0.605, 0.525),
                (-0.48, 0.32, 0.725, 0.606, 0.52),
                (-0.25, 0.31, 0.73, 0.59, 0.29),
                (0.08, 0.285, 0.70, 0.55, 0.23),
                (0.43, 0.25, 0.635, 0.52, 0.20),
                (0.84, 0.21, 0.55, 0.50, 0.195),
                (1.25, 0.15, 0.43, 0.54, 0.23),
                (1.62, 0.10, 0.23, 0.50, 0.31),
            ]
        )
        stations = [
            (
                z,
                ix,
                ox + width_delta,
                roof,
                belly
                - (p["inlet_height"] - (0.22 if ferrari else 0.17))
                * (1 if ferrari else 0.39)
                * (1 if z < -0.4 else 0)
                + (p["undercut"] - (0.12 if ferrari else 0.15))
                * (1 if -0.3 < z < 0.6 else 0),
            )
            for z, ix, ox, roof, belly in stations
        ]
        shell = pod_surface(
            ("broad_shoulder" if ferrari else "raised_rear_deck") + "_" + str(side),
            stations,
            side,
            red if ferrari else white,
            channel=0 if ferrari else 0.065,
        )
        # The slot's small height on W17 is supported visually; the actual
        # dimensions, internal radiator faces and duct routing remain unknown.
        outline = front_boundary(shell, stations[0][0])
        intake(
            ("forward_inlet" if ferrari else "slit_inlet") + "_" + str(side),
            outline,
            0.11,
            red if ferrari else carbon,
            black,
        )
        if not ferrari:
            # Project the original turquoise band onto the new ramp.
            paint_ribbon(
                "upper_turquoise_sweep",
                [
                    (side * 0.70, 0.585, -0.48),
                    (side * 0.70, 0.57, -0.22),
                    (side * 0.65, 0.52, 0.15),
                    (side * 0.575, 0.495, 0.55),
                    (side * 0.46, 0.51, 1.02),
                ],
                0.035,
                accent,
                shell,
            )
        # A body-attached lower edge, not a freestanding tube under the inlet.
        paint_ribbon(
            "lower_flow_line",
            [
                (side * 0.70, 0.31, -0.22),
                (side * 0.64, 0.235, 0.18),
                (side * 0.51, 0.205, 0.7),
                (side * 0.32, 0.205, 1.3),
            ],
            0.009 if ferrari else 0.014,
            accent,
            shell,
        )

    COMPONENT = "engine_cover"
    p = params[COMPONENT]
    engine_body = loft(
        "engine_body",
        [
            (0.22, 0.24, 0.46, 0.17),
            (0.34, 0.26, 0.47, 0.19),
            (0.66, 0.245 if ferrari else 0.205, 0.45, 0.205),
            (1.10, 0.19 if ferrari else 0.155, 0.375, 0.175),
            (1.56, p["tail_width"], 0.305, 0.13),
            (1.87, 0.06, 0.29, 0.065),
        ],
        red if ferrari else white,
    )
    loft(
        "upper_spine",
        (
            [
                (0.40, 0.10, 0.76, 0.155),
                (0.43, 0.13, 0.77, p["spine_height"] - 0.77),
                (0.53, 0.23, 0.66, 0.255),
                (0.81, 0.25, 0.59, 0.23),
                (1.12, 0.17, 0.51, 0.20),
                (1.49, 0.09, 0.40, 0.115),
                (1.68, 0.035, 0.34, 0.065),
            ]
            if ferrari
            else [
                (0.36, 0.115, 0.815, 0.11),
                (0.39, 0.145, 0.80, p["spine_height"] - 0.80),
                (0.58, 0.17, 0.72, 0.19),
                (0.88, 0.155, 0.65, 0.20),
                (1.20, 0.12, 0.57, 0.17),
                (1.56, 0.052, 0.45, 0.10),
                (1.70, 0.029, 0.335, 0.06),
            ]
        ),
        white,
        exponent=1.35 if ferrari else 0.82,
    )
    mouth = (
        [
            (-0.09, 0.755, 0.18),
            (-0.072, 0.87, 0.18),
            (-0.04, 0.922, 0.18),
            (0, 0.932, 0.18),
            (0.04, 0.922, 0.18),
            (0.072, 0.87, 0.18),
            (0.09, 0.755, 0.18),
            (0, 0.745, 0.18),
        ]
        if ferrari
        else [
            (-0.105, 0.79, 0.14),
            (-0.108, 0.86, 0.14),
            (-0.07, 0.905, 0.14),
            (0, 0.915, 0.14),
            (0.07, 0.905, 0.14),
            (0.108, 0.86, 0.14),
            (0.105, 0.79, 0.14),
            (0.07, 0.756, 0.14),
            (-0.07, 0.756, 0.14),
        ]
    )
    intake_cowl(mouth, carbon)
    intake("airbox", mouth, 0.16, carbon if ferrari else accent, black)
    if not ferrari:
        rod("airbox_divider", (0, 0.757, 0.14), (0, 0.91, 0.14), 0.005, carbon)
    rod("camera_support", (0, p["spine_height"], 0.40), (0, 1.04, 0.40), 0.012, carbon)
    rounded_box("onboard_camera", (0, 1.055, 0.40), (0.23, 0.038, 0.065), carbon, 0.014)
    fin = mesh(
        "dorsal_fin",
        (
            [
                (0, 0.925, 0.45),
                (0, 0.855, 0.82),
                (0, 0.69, 1.26),
                (0, 0.50, 1.64),
                (0, 0.345, 1.68),
                (0, 0.52, 0.8),
            ]
            if ferrari
            else [
                (0, 0.92, 0.43),
                (0, 0.87, 0.80),
                (0, 0.77, 1.19),
                (0, 0.70, 1.56),
                (0, 0.47, 1.66),
                (0, 0.51, 0.8),
            ]
        ),
        [(0, 1, 2, 3, 4, 5)],
        white,
    )
    fin.modifiers.new("Fin thickness", "SOLIDIFY").thickness = 0.009
    # Small cooling reliefs on the Ferrari's white shoulder are visible in the
    # rear launch image. Count/depth are illustrative, not an inferred radiator.
    if ferrari:
        for side in (-1, 1):
            for j in range(6):
                tube(
                    "shoulder_cooling_relief",
                    [
                        (side * 0.208, 0.628 - j * 0.015, 0.62 + j * 0.055),
                        (side * 0.25, 0.592 - j * 0.013, 0.64 + j * 0.055),
                    ],
                    0.0035,
                    carbon,
                )
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
    build_floor(team, p, carbon)
    rounded_box(
        "plank",
        (0, 0.055, 0.50),
        (0.22, 0.012, 2.85),
        material("Plank", (0.09, 0.065, 0.035), 0.8),
        0.005,
    )

    COMPONENT = "diffuser"
    p = params[COMPONENT]
    # Continuous ramp and joined walls, rather than a subdivided quad whose
    # rounded boundary leaves the flat strakes detached. Concealed channels
    # remain an estimated enclosure, not an inferred aerodynamic upgrade.
    ramp = [
        (1.12, 0.082),
        (1.38, 0.098),
        (1.70, p["exit_height"] * 0.62),
        (1.98, p["exit_height"] * 0.93),
        (2.15, p["exit_height"]),
    ]
    ruled_skin(
        "expansion_surface",
        [[z, -0.51, y, z, 0.51, y, z] for z, y in ramp],
        carbon,
        0.007,
    )
    for x in (-0.51, -0.27, 0, 0.27, 0.51):
        ruled_skin(
            "outlet_wall" if abs(x) > 0.5 else "estimated_channel_wall",
            [[z, x, 0.072, z, x, y + 0.003, z] for z, y in ramp],
            carbon,
            0.005,
        )
    ruled_skin(
        "outlet_laminate_return",
        [
            [
                0,
                -0.51,
                p["exit_height"] - 0.003,
                2.13,
                -0.51,
                p["exit_height"] + 0.008,
                2.158,
            ],
            [
                1,
                0.51,
                p["exit_height"] - 0.003,
                2.13,
                0.51,
                p["exit_height"] + 0.008,
                2.158,
            ],
        ],
        carbon,
        0.003,
    )

    COMPONENT = "rear_wing"
    p = params[COMPONENT]
    build_rear_wing(team, p, carbon)
    for side in (-1, 1):
        rounded_box(
            "led_strip", (side * 0.513, 0.80, 2.32), (0.015, 0.145, 0.012), lens, 0.005
        )
    rounded_box("rear_rain_light", (0, 0.32, 2.11), (0.075, 0.065, 0.025), lens, 0.009)

    COMPONENT = "suspension"
    for axle, z in (("front", -1.7), ("rear", 1.7)):
        for side in (-1, 1):
            x = side * (0.81 if axle == "front" else 0.76)
            surface = nose if axle == "front" else engine_body
            for h in (0.22, 0.44):
                for mount_z in (-1.78, -1.10) if axle == "front" else (1.36, 1.82):
                    mount = body_attachment(surface, side, h + 0.02, mount_z)
                    suspension_blade(
                        axle + "_wishbone",
                        mount,
                        (x, h, z),
                        carbon,
                    )
            rod(
                axle + "_pushrod",
                body_attachment(
                    surface, side, 0.52, -1.12 if axle == "front" else 1.48
                ),
                (x, 0.22, z),
                0.014,
                carbon,
            )
            rod(
                axle + "_trackrod",
                body_attachment(surface, side, 0.31, z - 0.10),
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
            rod(axle + "_upright", (x, 0.20, z), (x, 0.46, z), 0.024, carbon)
            if axle == "rear":
                rod(
                    "rear_halfshaft",
                    body_attachment(surface, side, 0.352, z),
                    (x, 0.352, z),
                    0.017,
                    alloy,
                )

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
    parser.add_argument(
        "--device",
        choices=("CPU", "METAL"),
        default="CPU",
        help="CPU for Docker; optional Metal for native macOS review renders",
    )
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
    shape_hashes = {}
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
        shape = hashlib.sha256()
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
            # Exclude materials to verify that constructor differences survive
            # the viewer's neutral finish and are not merely different paint.
            if not any(
                tag in obj.name
                for tag in ("flow_line", "turquoise_nose_line", "upper_turquoise_sweep")
            ):
                shape.update(json.dumps(polygons, separators=(",", ":")).encode())
            for mat in data.materials:
                h.update(material_hashes.get(mat.name, mat.name).encode())
            evaluated.to_mesh_clear()
        hashes[component] = h.hexdigest()
        shape_hashes[component] = shape.hexdigest()
    (out / "geometry.json").write_text(
        json.dumps(
            {
                "component_hashes": hashes,
                "shape_hashes": shape_hashes,
                "generator_version": "2026.5",
                "suspension_attachments": ATTACHMENTS,
            },
            indent=2,
        )
    )
    camera = studio()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    if args.device == "METAL":
        preferences = bpy.context.preferences.addons["cycles"].preferences
        preferences.compute_device_type = "METAL"
        preferences.refresh_devices()
        devices = [d for d in preferences.devices if d.type == "METAL"]
        if not devices:
            raise RuntimeError("No Metal device available; use --device CPU.")
        for device in preferences.devices:
            device.use = device.type == "METAL"
        scene.cycles.device = "GPU"
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

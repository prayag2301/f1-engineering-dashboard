"""Blender fixture: identical neutral cameras for front/rear wing comparisons."""
import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    outputs = [args.output / f"neutral_{wing}.png" for wing in ("front_wing", "rear_wing")]
    if any(p.exists() for p in outputs):
        raise FileExistsError("Keep reviewed images immutable; use a new output directory")
    args.output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(args.scene))
    scene = bpy.context.scene
    neutral = bpy.data.materials.new("Review neutral")
    neutral.use_nodes = True
    shader = neutral.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (.48, .48, .48, 1)
    shader.inputs["Roughness"].default_value = .48
    scene.cycles.samples = 48
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.resolution_percentage = 100
    for wing, position, target, output in zip(
        ("front_wing", "rear_wing"),
        ((2, 1.3, -4.5), (1.6, 1.3, 4)),
        ((0, .2, -2.25), (0, .64, 2)),
        outputs,
    ):
        visible = []
        for obj in scene.objects:
            if "component" in obj:
                obj.hide_render = obj["component"] != wing
                if not obj.hide_render:
                    visible.append(obj)
                    for slot in obj.material_slots:
                        slot.material = neutral
        assert visible, f"Missing {wing} assembly"
        camera = scene.camera
        camera.location = Vector((position[0], -position[2], position[1]))
        aim = Vector((target[0], -target[2], target[1]))
        camera.rotation_euler = (aim - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.lens = 52
        scene.render.filepath = str(output)
        bpy.ops.render.render(write_still=True)
        assert output.is_file(), f"Missing render: {output}"


if __name__ == "__main__":
    main()

"""Preview in a separate scene; never rewrite the user's camera or render settings."""
import math
import bpy
from mathutils import Vector


def render_preview(collection, spec, view, resolution, path):
    scene = bpy.data.scenes.new("Agentic preview")
    scene.collection.children.link(collection)
    created = []
    world = None
    try:
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 16
        scene.cycles.use_denoising = True
        scene.render.resolution_x = resolution
        scene.render.resolution_y = resolution
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(path)
        scene.render.film_transparent = False
        world = bpy.data.worlds.new("Agentic background")
        world.use_nodes = True
        world.node_tree.nodes["Background"].inputs[0].default_value = (0.035, 0.045, 0.065, 1)
        world.node_tree.nodes["Background"].inputs[1].default_value = 0.5
        scene.world = world
        size = max(spec["width_mm"], spec["height_mm"]) / 1000
        direction = {"front": (0, 0, 1), "back": (0, 0, -1),
                     "edge": (1, 0, 0), "perspective": (0.55, -0.55, 1)}[view]
        camera = bpy.data.cameras.new("Agentic camera")
        obj = bpy.data.objects.new("Agentic camera", camera)
        created.append(obj)
        scene.collection.objects.link(obj)
        obj.location = Vector(direction).normalized() * size * 3
        if view == "front":
            obj.rotation_euler = (0, 0, 0)
        elif view == "back":
            obj.rotation_euler = (0, math.pi, 0)
        else:
            obj.rotation_euler = (-obj.location).to_track_quat("-Z", "Y").to_euler()
        camera.type = "ORTHO"
        camera.ortho_scale = size * 1.2
        camera.clip_start, camera.clip_end = 0.00001, 100
        scene.camera = obj
        # Near-axis softboxes make reflective lettering readable on both faces.
        for location in [(0.15, 0.2, 1.5), (-0.8, 0.1, 1.2), (0.15, 0.2, -1.5)]:
            light = bpy.data.lights.new("Agentic softbox", "AREA")
            # The subject is only 85 mm wide; full-size studio wattage overexposes it.
            light.energy = 0.3 * (size / 0.085) ** 2
            light.shape, light.size = "DISK", size * 1.8
            lo = bpy.data.objects.new("Agentic softbox", light)
            created.append(lo)
            scene.collection.objects.link(lo)
            lo.location = Vector(location) * size * 2
            lo.rotation_euler = (-lo.location).to_track_quat("-Z", "Y").to_euler()
        bpy.ops.render.render(write_still=True, scene=scene.name)
    finally:
        bpy.data.scenes.remove(scene)
        for obj in created:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if isinstance(data, bpy.types.Camera):
                bpy.data.cameras.remove(data)
            else:
                bpy.data.lights.remove(data)
        if world:
            bpy.data.worlds.remove(world)

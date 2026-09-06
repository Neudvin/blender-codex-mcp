"""Main-thread Blender recipe runtime. Import only inside Blender."""
import copy
import json
import math
import os
from pathlib import Path
import uuid

import bpy
from mathutils import Vector

from . import VERSION
from .model import DomainError, canonical, digest, identifier, inside_convex, outline, prism, validate_spec, validate_text

STATE = "agentic_card_state"
ROLE = "agentic_role"


def cleanup(collection):
    """Only remove data owned by a disposable/generated collection."""
    materials = set()
    for obj in list(collection.objects):
        data = obj.data
        materials.update(m for m in getattr(data, "materials", []) if m)
        bpy.data.objects.remove(obj, do_unlink=True)
        if data and data.users == 0:
            if isinstance(data, bpy.types.Mesh):
                bpy.data.meshes.remove(data)
            elif isinstance(data, bpy.types.Curve):
                bpy.data.curves.remove(data)
    bpy.data.collections.remove(collection)
    for mat in materials:
        if mat.users == 0:
            bpy.data.materials.remove(mat)


def new_mesh(collection, role, points, low, high, material, bevel):
    vertices, faces = prism(points, low, high)
    mesh = bpy.data.meshes.new(role)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(role, mesh)
    collection.objects.link(obj)
    obj[ROLE] = role
    mesh.materials.append(material)
    if bevel:
        mod = obj.modifiers.new("Edge finish", "BEVEL")
        mod.width, mod.segments = bevel / 1000, 3
    return obj


def material(name, color, roughness, wood=False, angle=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = 0 if wood else 1
    shader.inputs["Roughness"].default_value = roughness
    if wood:
        coord = nodes.new("ShaderNodeTexCoord")
        mapping = nodes.new("ShaderNodeMapping")
        mapping.inputs["Rotation"].default_value[2] = math.radians(angle)
        mapping.inputs["Scale"].default_value = (4, 65, 5)
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 2
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*[c * 0.55 for c in color], 1)
        ramp.color_ramp.elements[1].color = (*[min(c * 1.4, 1) for c in color], 1)
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.12
        bump.inputs["Distance"].default_value = 0.000015
        links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
        links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return mat


def make_text(collection, text, spec, gold):
    curve = bpy.data.curves.new(text["id"], "FONT")
    obj = bpy.data.objects.new(text["id"], curve)
    collection.objects.link(obj)
    obj[ROLE] = "text:" + text["id"]
    curve.body = text["text"]
    curve.align_x, curve.align_y = "CENTER", "CENTER"
    curve.size = text["size_mm"] / 1000
    curve.space_character = text["tracking"]
    curve.extrude = 0.000005  # 0.005 mm visual lettering, not a fabrication specification.
    curve.materials.append(gold)
    if spec["font_path"]:
        p = Path(spec["font_path"]).expanduser()
        if p.suffix.lower() not in (".ttf", ".otf") or not p.is_file():
            raise DomainError("FONT_NOT_FOUND", "Provide an existing .ttf/.otf font path.")
        curve.font = bpy.data.fonts.load(str(p), check_existing=True)
    back = text["side"] == "back"
    sign = -1 if back else 1
    obj.location = (sign * text["x_mm"] / 1000, text["y_mm"] / 1000,
                    sign * (spec["core_mm"] / 2 + spec["veneer_mm"] + 0.006) / 1000)
    if back:
        obj.rotation_euler[1] = math.pi
    return obj


def make_emblem(collection, spec, gold):
    """An original small branching-tree placeholder; not a traced L'Arbre logo."""
    cut = spec["corner_cut_mm"]
    if cut < 4:
        return
    curve = bpy.data.curves.new("Tree approximation", "CURVE")
    curve.dimensions, curve.bevel_depth, curve.bevel_resolution = "3D", 0.00006, 2
    obj = bpy.data.objects.new("Tree approximation", curve)
    obj[ROLE] = "emblem"
    collection.objects.link(obj)
    curve.materials.append(gold)
    x = spec["width_mm"] / 2 - spec["border_mm"] - cut * 0.23
    y = -spec["height_mm"] / 2 + spec["border_mm"] + cut * 0.23
    size = min(cut * 0.14, 2)
    paths = [[(0, -1), (0, 1)], [(-0.8, -1), (0, -0.6), (0.8, -1)],
             [(-1, 0.4), (0, 0), (1, 0.4)], [(-0.8, 1), (0, 0.5), (0.8, 1)],
             [(-0.5, 1.3), (0, 0.9), (0.5, 1.3)]]
    for path in paths:
        spline = curve.splines.new("POLY")
        spline.points.add(len(path) - 1)
        for point, (px, py) in zip(spline.points, path):
            point.co = ((x + px * size) / 1000, (y + py * size) / 1000,
                        (spec["core_mm"] / 2 + 0.02) / 1000, 1)


def stage(spec):
    """Build in a temporary scene; a failed fit never changes the live asset."""
    coll = bpy.data.collections.new("Card staging")
    scene = bpy.data.scenes.new("Card validation")
    scene.collection.children.link(coll)
    try:
        gold = material("Card gold", spec["gold_color"], spec["gold_roughness"])
        new_mesh(coll, "core", outline(spec["width_mm"], spec["height_mm"]),
                 -spec["core_mm"] / 2, spec["core_mm"] / 2, gold, spec["bevel_mm"])
        wood = material("Card veneer", spec["wood_color"], spec["wood_roughness"], True, spec["grain_angle_deg"])
        face = outline(spec["width_mm"] - 2 * spec["border_mm"],
                       spec["height_mm"] - 2 * spec["border_mm"], spec["corner_cut_mm"])
        z = spec["core_mm"] / 2
        new_mesh(coll, "veneer_front", face, z, z + spec["veneer_mm"], wood, spec["bevel_mm"])
        new_mesh(coll, "veneer_back", face, -z - spec["veneer_mm"], -z, wood, spec["bevel_mm"])
        for text in spec["texts"]:
            make_text(coll, text, spec, gold)
        make_emblem(coll, spec, gold)
        layer = scene.view_layers[0]
        layer.update()
        with bpy.context.temp_override(scene=scene, view_layer=layer):
            depsgraph = bpy.context.evaluated_depsgraph_get()
            depsgraph.update()
            rectangles = {"front": [], "back": []}
            for text in spec["texts"]:
                obj = next(o for o in coll.objects if o[ROLE] == "text:" + text["id"])
                evaluated = obj.evaluated_get(depsgraph)
                corners = [obj.matrix_world @ Vector(v) for v in evaluated.bound_box]
                if not corners or evaluated.dimensions.x <= 0:
                    raise DomainError("TEXT_LAYOUT_FAILED", "Unable to evaluate text bounds.", field=text["id"])
                xy = [(v.x * 1000, v.y * 1000) for v in corners]
                if not all(inside_convex(p, face, 0.15) for p in xy):
                    raise DomainError("TEXT_OVERFLOW", "Text does not fit the veneer. Adjust size or position explicitly.", field=text["id"])
                box = (min(p[0] for p in xy), min(p[1] for p in xy), max(p[0] for p in xy), max(p[1] for p in xy))
                for previous, b in rectangles[text["side"]]:
                    if min(box[2], b[2]) > max(box[0], b[0]) and min(box[3], b[3]) > max(box[1], b[1]):
                        raise DomainError("TEXT_OVERLAP", "Text fields overlap.", fields=[previous, text["id"]])
                rectangles[text["side"]].append((text["id"], box))
        return coll
    except Exception:
        cleanup(coll)
        raise
    finally:
        bpy.data.scenes.remove(scene)


def fingerprint(coll):
    """Fingerprint supported recipe geometry, transforms, text, shaders and links."""
    objects = []
    for o in coll.objects:
        row = {"role": o.get(ROLE), "type": o.type, "matrix": [list(v) for v in o.matrix_world],
               "parent": o.parent.name if o.parent else None, "hidden": [o.hide_render, o.hide_viewport],
               "constraints": len(o.constraints), "animation": bool(o.animation_data or getattr(o.data, "animation_data", None))}
        if o.type == "MESH":
            row["mesh"] = [[list(v.co) for v in o.data.vertices], [list(p.vertices) for p in o.data.polygons]]
            row["modifiers"] = [(m.type, m.width, m.segments, m.show_viewport, m.show_render) if m.type == "BEVEL" else (m.type, m.name) for m in o.modifiers]
        elif o.type == "FONT":
            d = o.data
            row["text"] = [d.body, d.size, d.space_character, d.align_x, d.align_y, d.extrude, d.font.filepath]
        elif o.type == "CURVE":
            row["curve"] = [o.data.bevel_depth, [[list(p.co) for p in s.points] for s in o.data.splines]]
        mats = []
        for m in getattr(o.data, "materials", []):
            if not m:
                mats.append(None)
                continue
            nodes = []
            for n in m.node_tree.nodes if m.use_nodes else []:
                vals = []
                for sock in n.inputs:
                    v = getattr(sock, "default_value", None)
                    vals.append(v if isinstance(v, (float, int, str, bool, type(None))) else list(v) if hasattr(v, "__iter__") else repr(v))
                nodes.append([n.name, n.bl_idname, vals, [(e.position, list(e.color)) for e in n.color_ramp.elements] if hasattr(n, "color_ramp") else None])
            mats.append([list(m.diffuse_color), m.use_nodes, nodes,
                         [(l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier) for l in m.node_tree.links] if m.use_nodes else []])
        row["materials"] = mats
        objects.append(row)
    return digest(sorted(objects, key=lambda x: str(x["role"])))


class Runtime:
    def __init__(self, output_root=None):
        self.output_root = Path(output_root or Path.home() / "BlenderAgenticMCP").expanduser().resolve()
        self.epoch = uuid.uuid4().hex

    def assets(self):
        return [c for c in bpy.context.scene.collection.children if STATE in c]

    def resolve(self, ref):
        matches = [c for c in self.assets() if json.loads(c[STATE])["ref"] == ref]
        if len(matches) != 1:
            raise DomainError("NOT_FOUND" if not matches else "AMBIGUOUS_REFERENCE", "Expected exactly one card with this reference in the active scene.")
        return matches[0], json.loads(matches[0][STATE])

    def unchanged(self, coll, state, expected):
        if type(expected) is not int or expected != state["revision"]:
            raise DomainError("STALE_REVISION", "Inspect the card and retry against its current revision.", revision=state["revision"])
        if fingerprint(coll) != state["fingerprint"]:
            raise DomainError("MANUAL_EDIT_CONFLICT", "Generated content changed in Blender. Preserve or duplicate it before regenerating.")
        if len(coll.children) or coll.library or coll.users != 1:
            raise DomainError("EXTERNAL_DEPENDENCY", "Card collection is shared, linked, or contains child collections.")
        owned = set(coll.objects)
        for obj, users in bpy.data.user_map(subset=owned).items():
            # Blender also reports the containing scene as an indirect user.
            if users - owned - {coll, bpy.context.scene}:
                raise DomainError("EXTERNAL_DEPENDENCY", "Another data-block refers to a generated card component.", component=obj.get(ROLE))
        for obj in owned:
            if tuple(obj.users_collection) != (coll,):
                raise DomainError("EXTERNAL_DEPENDENCY", "Card component is linked into another collection.")
            if obj.data.users != 1:
                raise DomainError("EXTERNAL_DEPENDENCY", "Generated geometry is shared with another object.")

    def summary(self, coll, state, include_spec=False):
        result = {"ok": True, "asset_ref": state["ref"], "revision": state["revision"],
                  "objects": len(coll.objects), "units": "mm", "manual_changes": fingerprint(coll) != state["fingerprint"],
                  "checks": {"text_fit": "pass", "text_overlap": "pass", "self_intersection": "unknown"},
                  "notes": ["Tree emblem is an approximation.", "Built-in font is a substitute." if not state["spec"]["font_path"] else "User font selected."]}
        if result["manual_changes"]:
            result["checks"]["text_fit"] = result["checks"]["text_overlap"] = "unknown"
        if include_spec:
            result["spec"] = state["spec"]
        return result

    def dispatch(self, op, args):
        try:
            handlers = {"status": self.status, "inspect": self.inspect, "create": self.create,
                        "update": self.update, "text_set": self.text_set, "history": self.history,
                        "restore": self.restore, "preview": self.preview, "save": self.save}
            if op not in handlers:
                raise DomainError("UNSUPPORTED_OPERATION", "Discover the supported operations with status.")
            return handlers[op](**args)
        except DomainError as exc:
            return exc.result()
        except (TypeError, ValueError, KeyError) as exc:
            return DomainError("INVALID_ARGUMENT", str(exc)).result()
        except Exception as exc:
            return DomainError("BLENDER_ERROR", str(exc)).result()

    def status(self):
        return {"ok": True, "version": VERSION, "blender": bpy.app.version_string, "epoch": self.epoch,
                "execution_mode": "headless" if bpy.app.background else "live_gui",
                "operations": ["inspect", "create", "update", "text_set", "history", "restore", "preview", "save"],
                "output_root": str(self.output_root),
                "assets": [{"asset_ref": json.loads(c[STATE])["ref"], "name": c.name} for c in self.assets()]}

    def inspect(self, asset_ref=None, offset=0, limit=20):
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise DomainError("INVALID_ARGUMENT", "offset >= 0 and limit 1–100 are required.")
        if asset_ref is None:
            objects = list(bpy.context.scene.objects)
            rows = [{"name": o.name, "type": o.type, "location_m": list(o.location), "role": o.get(ROLE)} for o in objects[offset:offset + limit]]
            return {"ok": True, "total": len(objects), "objects": rows, "next_offset": offset + limit if offset + limit < len(objects) else None}
        coll, state = self.resolve(asset_ref)
        result = self.summary(coll, state, True)
        result["components"] = [{"ref": asset_ref + "/" + o[ROLE] if ROLE in o else None, "name": o.name, "type": o.type,
                                  **({"text": o.data.body} if o.type == "FONT" else {})} for o in list(coll.objects)[offset:offset + limit]]
        result["next_offset"] = offset + limit if offset + limit < len(coll.objects) else None
        return result

    def request_check(self, request_id, payload):
        identifier(request_id, "request_id")
        h = digest(payload)
        for coll in self.assets():
            state = json.loads(coll[STATE])
            for record in state["requests"]:
                if record["id"] == request_id:
                    if record["hash"] != h:
                        raise DomainError("IDEMPOTENCY_CONFLICT", "request_id was already used with different arguments.")
                    return h, {**record["result"], "replayed": True, "current_revision": state["revision"]}
        return h, None

    def create(self, spec, request_id):
        h, replay = self.request_check(request_id, {"op": "create", "spec": spec})
        if replay:
            return replay
        if bpy.context.mode != "OBJECT":
            raise DomainError("INVALID_MODE", "Switch Blender to Object Mode before constructing a card.")
        normalized = validate_spec(spec)
        state = {"ref": "card:" + uuid.uuid4().hex, "revision": 1, "spec": normalized, "history": [], "requests": []}
        return self.commit(None, state, normalized, request_id, h)

    def change(self, asset_ref, expected_revision, request_id, payload, edit):
        h, replay = self.request_check(request_id, payload)
        if replay:
            return replay
        if bpy.context.mode != "OBJECT":
            raise DomainError("INVALID_MODE", "Switch Blender to Object Mode before regenerating a card.")
        coll, state = self.resolve(asset_ref)
        self.unchanged(coll, state, expected_revision)
        candidate = validate_spec(edit(copy.deepcopy(state["spec"]), state))
        updated = copy.deepcopy(state)
        updated["history"].append({"revision": state["revision"], "spec": state["spec"]})
        updated["history"] = updated["history"][-32:]
        updated["revision"] += 1
        return self.commit(coll, updated, candidate, request_id, h)

    def commit(self, old, state, spec, request_id, request_hash):
        staged = stage(spec)
        try:
            state["spec"] = spec
            state["fingerprint"] = fingerprint(staged)
            result = self.summary(staged, state)
            state["requests"].append({"id": request_id, "hash": request_hash, "result": result})
            # Fail explicitly before the replay ledger could be truncated.
            if len(state["requests"]) > 256:
                raise DomainError("LEDGER_FULL", "Prototype limit reached: 256 mutations per card. Save and start a new asset.")
            staged[STATE] = canonical(state)
            staged.name = "LArbre Card " + state["ref"][-8:]
            bpy.context.scene.collection.children.link(staged)
            if old:
                bpy.context.scene.collection.children.unlink(old)
        except Exception:
            cleanup(staged)
            raise
        if old:
            # The swap is committed. A cleanup failure must not report a failed edit.
            try:
                cleanup(old)
            except Exception:
                result["cleanup_pending"] = True
        bpy.context.view_layer.update()
        return result

    def update(self, asset_ref, expected_revision, changes, request_id):
        allowed = set(validate_spec({})) - {"texts"}
        if not isinstance(changes, dict) or not changes or set(changes) - allowed:
            raise DomainError("INVALID_ARGUMENT", "Provide supported card parameters; edit text with text_set.")
        payload = dict(op="update", asset_ref=asset_ref, expected_revision=expected_revision, changes=changes)
        return self.change(asset_ref, expected_revision, request_id, payload, lambda spec, _: {**spec, **changes})

    def text_set(self, asset_ref, expected_revision, text, request_id):
        if not isinstance(text, dict) or "id" not in text:
            raise DomainError("INVALID_ARGUMENT", "Text edit requires an id.")
        identifier(text["id"], "text id")
        payload = dict(op="text_set", asset_ref=asset_ref, expected_revision=expected_revision, text=text)
        def edit(spec, _):
            previous = next((x for x in spec["texts"] if x["id"] == text["id"]), {})
            t = validate_text({**previous, **text})
            spec["texts"] = [t if x["id"] == t["id"] else x for x in spec["texts"]]
            if not any(x["id"] == t["id"] for x in spec["texts"]):
                spec["texts"].append(t)
            return spec
        return self.change(asset_ref, expected_revision, request_id, payload, edit)

    def history(self, asset_ref):
        _, state = self.resolve(asset_ref)
        return {"ok": True, "revision": state["revision"], "available_revisions": [h["revision"] for h in state["history"]],
                "scope": "generated card recipe; does not undo manual edits or external files"}

    def restore(self, asset_ref, expected_revision, revision, request_id, parameters=None):
        def edit(spec, state):
            previous = next((h["spec"] for h in state["history"] if h["revision"] == revision), None)
            if previous is None:
                raise DomainError("NOT_FOUND", "Revision is outside the retained history.")
            if parameters is None:
                return copy.deepcopy(previous)
            if not isinstance(parameters, list) or not parameters or any(p not in spec for p in parameters):
                raise DomainError("INVALID_ARGUMENT", "Provide a nonempty list of valid parameter names.")
            return {**spec, **{p: copy.deepcopy(previous[p]) for p in parameters}}
        return self.change(asset_ref, expected_revision, request_id,
                           dict(op="restore", asset_ref=asset_ref, expected_revision=expected_revision, revision=revision, parameters=parameters), edit)

    def artifact_path(self, filename, suffix):
        if not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith(suffix):
            raise DomainError("INVALID_ARGUMENT", f"Provide a filename ending in {suffix}, without directories.")
        identifier(filename[:-len(suffix)], "filename stem")
        self.output_root.mkdir(parents=True, exist_ok=True)
        path = self.output_root / filename
        if path.exists():
            raise DomainError("FILE_EXISTS", "Choose a new filename; artifacts are never overwritten.")
        return path

    def preview(self, asset_ref, view="front", resolution=768):
        from .rendering import render_preview
        coll, state = self.resolve(asset_ref)
        if view not in ("front", "back", "edge", "perspective") or type(resolution) is not int or not 128 <= resolution <= 1024:
            raise DomainError("INVALID_ARGUMENT", "Choose a standard view and a resolution from 128 to 1024.")
        path = self.artifact_path("preview_" + uuid.uuid4().hex + ".png", ".png")
        render_preview(coll, state["spec"], view, resolution, path)
        return {"ok": True, "path": str(path), "view": view, "revision": state["revision"], "resolution": resolution}

    def save(self, asset_ref, filename):
        coll, state = self.resolve(asset_ref)
        if fingerprint(coll) != state["fingerprint"]:
            raise DomainError("MANUAL_EDIT_CONFLICT", "Save manual edits through Blender before exporting a recipe artifact.")
        path = self.artifact_path(filename, ".blend")
        temp = path.with_name("." + uuid.uuid4().hex + ".blend")
        scene = bpy.data.scenes.new("LArbre card")
        scene.unit_settings.system = "METRIC"
        scene.collection.children.link(coll)
        try:
            bpy.data.libraries.write(str(temp), {scene}, path_remap="ABSOLUTE", fake_user=True)
            # Link instead of replace: atomic creation fails if a target appeared concurrently.
            os.link(temp, path)
        finally:
            bpy.data.scenes.remove(scene)
            temp.unlink(missing_ok=True)
        return {"ok": True, "path": str(path), "revision": state["revision"], "scope": "card-only .blend; active project unchanged"}

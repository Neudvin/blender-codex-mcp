"""Run with Blender --background --factory-startup --python-exit-code 1 --python this_file.

Set AGENTIC_TEST_RENDER=1 to include the four standard CPU renders.
Artifacts go to test-output and are not committed.
"""
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import bpy
from blender_codex_mcp.agentic.runtime import Runtime, STATE, ROLE, fingerprint

output = ROOT / "test-output" / uuid.uuid4().hex
runtime = Runtime(output)


def call(op, **args):
    result = runtime.dispatch(op, args)
    assert result["ok"], (op, result)
    return result


def fail(op, code, **args):
    result = runtime.dispatch(op, args)
    assert not result["ok"] and result["error"]["code"] == code, result


def counts():
    return tuple(len(getattr(bpy.data, key)) for key in ("objects", "meshes", "curves", "materials", "collections", "scenes"))


# Preserve an unrelated scene object and test >10 scene objects with pagination.
sentinel = bpy.data.objects.new("User sentinel", None)
bpy.context.scene.collection.objects.link(sentinel)
for i in range(15):
    obj = bpy.data.objects.new(f"Extra {i}", None)
    bpy.context.scene.collection.objects.link(obj)
page = call("inspect", limit=10)
assert page["total"] > 10 and page["next_offset"] == 10
assert len(call("inspect", offset=10, limit=100)["objects"]) == page["total"] - 10

created = call("create", spec={}, request_id="create-1")
ref = created["asset_ref"]
assert created["revision"] == 1
assert call("create", spec={}, request_id="create-1")["replayed"]
fail("create", "IDEMPOTENCY_CONFLICT", spec={"width_mm": 90}, request_id="create-1")
assert len(runtime.assets()) == 1
fail("create", "CARD_ALREADY_EXISTS", spec={}, request_id="accidental-duplicate")
assert len(runtime.assets()) == 1

original = call("inspect", asset_ref=ref)["spec"]
call("text_set", asset_ref=ref, expected_revision=1, request_id="email-1",
     text={"id": "email", "text": "HELLO@EXAMPLE.COM"})
new = call("inspect", asset_ref=ref)["spec"]
before = next(t for t in original["texts"] if t["id"] == "email")
after = next(t for t in new["texts"] if t["id"] == "email")
assert after == {**before, "text": "HELLO@EXAMPLE.COM"}
assert all(a == b for a, b in zip(original["texts"], new["texts"]) if a["id"] != "email")

coll, state = runtime.resolve(ref)
stable = fingerprint(coll), coll[STATE], counts()
fail("text_set", "TEXT_OVERFLOW", asset_ref=ref, expected_revision=2, request_id="overflow-1",
     text={"id": "email", "text": "W" * 100})
assert (fingerprint(coll), coll[STATE], counts()) == stable
fail("update", "STALE_REVISION", asset_ref=ref, expected_revision=1,
     request_id="stale-1", changes={"corner_cut_mm": 10})

call("update", asset_ref=ref, expected_revision=2, request_id="corner-1", changes={"corner_cut_mm": 10})
call("restore", asset_ref=ref, expected_revision=3, revision=1, parameters=["corner_cut_mm"], request_id="restore-1")
spec = call("inspect", asset_ref=ref)["spec"]
assert spec["corner_cut_mm"] == original["corner_cut_mm"]
assert next(t for t in spec["texts"] if t["id"] == "email")["text"] == "HELLO@EXAMPLE.COM"
assert bpy.data.objects.get("User sentinel") == sentinel

coll, state = runtime.resolve(ref)
core = next(o for o in coll.objects if o[ROLE] == "core")
old_x = core.location.x
core.location.x += 0.001
bpy.context.view_layer.update()
fail("update", "MANUAL_EDIT_CONFLICT", asset_ref=ref, expected_revision=4,
     request_id="manual-1", changes={"wood_roughness": 0.7})
core.location.x = old_x
bpy.context.view_layer.update()
constraint = sentinel.constraints.new("COPY_LOCATION")
constraint.target = core
fail("update", "EXTERNAL_DEPENDENCY", asset_ref=ref, expected_revision=4,
     request_id="external-1", changes={"wood_roughness": 0.7})
sentinel.constraints.remove(constraint)

if os.environ.get("AGENTIC_TEST_RENDER") == "1":
    active = bpy.context.scene
    stable_counts = counts()
    for view in ("front", "back", "edge", "perspective"):
        rendered = call("preview", asset_ref=ref, view=view, resolution=512)
        assert Path(rendered["path"]).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        assert bpy.context.scene == active and counts() == stable_counts

# The first save establishes one complete project file; later saves update it.
fail("save", "FILENAME_REQUIRED", expected_filepath="")
project = call("save", expected_filepath="", filename="working-project.blend")
project_path = project["path"]
assert bpy.data.filepath == project_path and project["first_save"]
fail("save", "PROJECT_MISMATCH", expected_filepath="")
fail("save", "SAVE_AS_NOT_SUPPORTED", expected_filepath=project_path, filename="another.blend")
call("text_set", asset_ref=ref, expected_revision=4, request_id="rotation-1",
     text={"id": "name", "rotation_deg": 90})
assert len(runtime.assets()) == 1
coll, state = runtime.resolve(ref)
import math
name = next(o for o in coll.objects if o.get(ROLE) == "text:name")
assert abs(math.degrees(name.rotation_euler.z) - 90) < 0.001
same = call("save", expected_filepath=project_path)
assert same["path"] == project_path and not same["first_save"]
assert Path(project_path + "1").is_file()  # Native Blender previous-save backup.

# Simulate a separate process touching the saved file. Never overwrite blindly.
stat = Path(project_path).stat()
os.utime(project_path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000000))
fail("save", "PROJECT_DISK_CONFLICT", expected_filepath=project_path)
os.utime(project_path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
runtime.project_saved()  # Reconciled by the test; production uses Blender save/load events.

saved = call("export", asset_ref=ref, filename="card.blend")
fail("export", "FILE_EXISTS", asset_ref=ref, filename="card.blend")
fail("export", "INVALID_ARGUMENT", asset_ref=ref, filename="../escape.blend")
assert bpy.data.filepath == project_path
assert bpy.data.objects.get("User sentinel") == sentinel

bpy.ops.wm.open_mainfile(filepath=project_path)
runtime = Runtime(output)
assert bpy.data.objects.get("User sentinel") is not None
assert call("inspect", asset_ref=ref)["revision"] == 5
assert next(t for t in call("inspect", asset_ref=ref)["spec"]["texts"] if t["id"] == "name")["rotation_deg"] == 90

# Reopen the actual file, then edit again using persisted state/replay ledger.
bpy.ops.wm.open_mainfile(filepath=saved["path"])
runtime = Runtime(output)
assert call("inspect", asset_ref=ref)["revision"] == 5
assert len(bpy.context.scene.objects) == created["objects"]
assert call("create", spec={}, request_id="create-1")["replayed"]
call("update", asset_ref=ref, expected_revision=5, request_id="reopen-1", changes={"gold_roughness": 0.3})
assert call("inspect", asset_ref=ref)["revision"] == 6
print("AGENTIC_INTEGRATION_PASS", bpy.app.version_string, str(output))

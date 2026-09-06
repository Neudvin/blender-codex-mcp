"""Disposable headless host for test_stdio_blender.py; not a production daemon."""
from pathlib import Path
import sys
import time

import bpy
import addon_utils

folder = Path(sys.argv[sys.argv.index("--") + 1])
sys.path.insert(0, str(folder / "addons"))
addon_utils.enable("blender_agentic_mcp", default_set=True)
import blender_agentic_mcp as addon
prefs = bpy.context.preferences.addons["blender_agentic_mcp"].preferences
prefs.port = int((folder / "port").read_text())
prefs.output_root = str(folder / "output")
assert bpy.ops.agentic_card.start() == {"FINISHED"}
(folder / "ready").touch()
deadline = time.monotonic() + 90
try:
    # Background Blender does not run the GUI timer event loop.
    while not (folder / "stop").exists() and time.monotonic() < deadline:
        addon.tick()
        time.sleep(0.005)
finally:
    addon_utils.disable("blender_agentic_mcp", default_set=True)
assert not bpy.app.timers.is_registered(addon.tick)
assert addon.on_load not in bpy.app.handlers.load_pre
assert addon.on_save not in bpy.app.handlers.save_post
print("PACKAGED_ADDON_PASS")

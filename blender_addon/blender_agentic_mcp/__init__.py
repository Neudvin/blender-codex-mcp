"""Install the ZIP built by scripts/build_agentic_addon.py, not this folder alone."""
bl_info = {
    "name": "Blender Agentic Card MCP", "author": "Blender Codex MCP contributors",
    "version": (0, 2, 0), "blender": (4, 5, 0), "category": "Interface",
    "location": "View3D > Sidebar > Agentic Card",
    "description": "Typed conversational business-card prototype over authenticated loopback",
}

import bpy
from bpy.app.handlers import persistent
from .agentic.bridge import Bridge
from .agentic.runtime import Runtime

_bridge = None


def tick():
    if _bridge is None:
        return None
    try:
        return _bridge.tick()
    except Exception as exc:
        print("Agentic Card bridge stopped:", exc)
        stop()
        return None


def stop():
    global _bridge
    if bpy.app.timers.is_registered(tick):
        bpy.app.timers.unregister(tick)
    if _bridge is not None:
        _bridge.close()
        _bridge = None


@persistent
def on_load(_):
    stop()


@persistent
def on_save(_):
    if _bridge is not None:
        _bridge.runtime.project_saved()


class AGENTICCARD_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    port: bpy.props.IntProperty(name="Port", default=9877, min=1024, max=65535)
    output_root: bpy.props.StringProperty(name="Output folder", subtype="DIR_PATH")

    def draw(self, context):
        self.layout.prop(self, "port")
        self.layout.prop(self, "output_root")
        self.layout.label(text="Restart the bridge after changing settings.")


class AGENTICCARD_OT_start(bpy.types.Operator):
    bl_idname = "agentic_card.start"
    bl_label = "Start MCP"

    def execute(self, context):
        global _bridge
        if _bridge is not None:
            return {"FINISHED"}
        prefs = context.preferences.addons[__package__].preferences
        try:
            folder = bpy.path.abspath(prefs.output_root) if prefs.output_root else None
            _bridge = Bridge(Runtime(folder), prefs.port)
            bpy.app.timers.register(tick, first_interval=0.025)
        except Exception as exc:
            stop()
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return {"FINISHED"}


class AGENTICCARD_OT_stop(bpy.types.Operator):
    bl_idname = "agentic_card.stop"
    bl_label = "Stop MCP"

    def execute(self, context):
        stop()
        return {"FINISHED"}


class AGENTICCARD_PT_panel(bpy.types.Panel):
    bl_label = "Agentic Card MCP"
    bl_idname = "AGENTICCARD_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Agentic Card"

    def draw(self, context):
        self.layout.label(text="Running on loopback" if _bridge else "Stopped")
        self.layout.operator("agentic_card.stop" if _bridge else "agentic_card.start")


CLASSES = (AGENTICCARD_Preferences, AGENTICCARD_OT_start, AGENTICCARD_OT_stop, AGENTICCARD_PT_panel)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.app.handlers.load_pre.append(on_load)
    bpy.app.handlers.save_post.append(on_save)


def unregister():
    stop()
    if on_load in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(on_load)
    if on_save in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(on_save)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

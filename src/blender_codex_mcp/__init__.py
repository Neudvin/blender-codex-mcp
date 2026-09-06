"""Codex-focused Blender integration through the Model Context Protocol."""

__version__ = "1.5.5"

# Preserve legacy imports without loading the raw-code server for other profiles.
def __getattr__(name):
    if name in {"BlenderConnection", "get_blender_connection"}:
        from . import server
        return getattr(server, name)
    raise AttributeError(name)

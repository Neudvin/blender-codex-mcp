"""Build a reproducible, dependency-free Blender add-on ZIP from shared sources."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(destination=None):
    destination = Path(destination or ROOT / "dist" / "blender_agentic_mcp.zip")
    destination.parent.mkdir(parents=True, exist_ok=True)
    sources = {"__init__.py": ROOT / "blender_addon/blender_agentic_mcp/__init__.py",
               "LICENSE": ROOT / "LICENSE"}
    sources.update({"agentic/" + p.name: p for p in (ROOT / "src/blender_codex_mcp/agentic").glob("*.py")})
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(sources.items()):
            info = zipfile.ZipInfo("blender_agentic_mcp/" + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return destination


if __name__ == "__main__":
    print(build())


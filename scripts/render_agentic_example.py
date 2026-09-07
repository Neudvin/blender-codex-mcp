"""Developer reference render; run inside Blender with --python-exit-code 1.

Optional environment variables: AGENTIC_EXAMPLE_FONT (local .ttf/.otf),
AGENTIC_EXAMPLE_OUTPUT (new artifact folder). Uses the same typed runtime as MCP.
"""
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from blender_codex_mcp.agentic.runtime import Runtime

spec = json.loads((ROOT / "examples/agentic_larbre_card.json").read_text())
if os.environ.get("AGENTIC_EXAMPLE_FONT"):
    spec["font_path"] = os.environ["AGENTIC_EXAMPLE_FONT"]
output = Path(os.environ.get("AGENTIC_EXAMPLE_OUTPUT", str(ROOT / "test-output" / uuid.uuid4().hex)))
runtime = Runtime(output)
card = runtime.create(spec, "reference-example")
manifest = {"card": card, "font": spec.get("font_path", "Blender built-in")}
for view in ("front", "back", "perspective"):
    manifest[view] = runtime.preview(card["asset_ref"], view, 768)
manifest["blend"] = runtime.export(card["asset_ref"], "reference-card.blend")
(output / "manifest.json").write_text(json.dumps(manifest, indent=2))
print("REFERENCE_EXAMPLE_PASS", output)

"""Small typed MCP profile. Blender owns all construction and validation logic."""
from dataclasses import asdict
import base64
import os
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, ImageContent, TextContent, ToolAnnotations

from .agentic.model import CardSpec, CardPatch, TextPatch, NativeCardObjects, DomainError, canonical
from .agentic.wire import Client

mcp = FastMCP("Blender Agentic Card", instructions=(
    "Create/edit layered or recessed business cards in millimetres. Inspect before editing. "
    "Use current revision and a fresh request_id per mutation; reuse the SAME id and "
    "arguments only when retrying an uncertain outcome. Request images only when useful. "
    "Text edits preserve omitted properties. Never claim token savings or fabrication readiness."
    " Keep working on the same asset and live project. Read card_status to identify its filepath; "
    "do not infer the current card from output filenames. Use card_update for dimension changes, "
    "card_text_set for text/rotation, and card_save for the current complete project. "
    "Use card_export only for an explicitly requested separate copy. Never silently switch to "
    "a background Blender process or create a replacement when a tool is unavailable. "
    "If a card already exists as native Blender geometry, use card_inspect then card_adopt "
    "with the exact mesh/text object names; subsequent edits stay in that same project."
))
client = Client(port=int(os.environ.get("BLENDER_AGENTIC_PORT", "9877")))


def annotation(read=False, replay=False):
    return ToolAnnotations(readOnlyHint=read, destructiveHint=not read,
                           idempotentHint=read or replay, openWorldHint=False)


def call(op, **args):
    try:
        result = client.call(op, args)
    except DomainError as exc:
        result = exc.result()
    return CallToolResult(isError=not result.get("ok", False),
                          content=[TextContent(type="text", text=canonical(result))],
                          structuredContent=result)


@mcp.tool(annotations=annotation(read=True))
def card_status() -> CallToolResult:
    """Discover connection, Blender version, active card references and output folder."""
    return call("status")


@mcp.tool(annotations=annotation(read=True))
def card_inspect(asset_ref: str | None = None, offset: int = 0, limit: int = 20) -> CallToolResult:
    """Read card parameters/components, or paginate scene objects when ref is omitted."""
    return call("inspect", asset_ref=asset_ref, offset=offset, limit=limit)


@mcp.tool(annotations=annotation(replay=True))
def card_create(request_id: str, spec: CardSpec | None = None, allow_additional: bool = False) -> CallToolResult:
    """Create a NEW layered or recessed card. To edit an existing card use card_update. Additional cards require explicit intent."""
    return call("create", spec=asdict(spec or CardSpec()), request_id=request_id, allow_additional=allow_additional)


@mcp.tool(annotations=annotation(replay=True))
def card_adopt(expected_filepath: str, request_id: str, objects: NativeCardObjects) -> CallToolResult:
    """Adopt four existing native mesh objects (body, front_veneer, back_veneer, web) and optional FONT names.

    This preserves the source meshes/materials and makes text, thickness, recess and save operations conversational.
    """
    return call("adopt", expected_filepath=expected_filepath, request_id=request_id, objects=asdict(objects))


@mcp.tool(annotations=annotation(replay=True))
def card_update(asset_ref: str, expected_revision: int, request_id: str, changes: CardPatch) -> CallToolResult:
    """Change specified geometry/material parameters; validate fit before swapping the recipe."""
    return call("update", asset_ref=asset_ref, expected_revision=expected_revision,
                request_id=request_id, changes={k: v for k, v in asdict(changes).items() if v is not None})


@mcp.tool(annotations=annotation(replay=True))
def card_text_set(asset_ref: str, expected_revision: int, request_id: str, text: TextPatch) -> CallToolResult:
    """Edit a text id, preserving omitted fields. A new id requires text; side defaults to front."""
    return call("text_set", asset_ref=asset_ref, expected_revision=expected_revision,
                request_id=request_id, text={k: v for k, v in asdict(text).items() if v is not None})


@mcp.tool(annotations=annotation(read=True))
def card_history(asset_ref: str) -> CallToolResult:
    """List retained recipe revisions (last 32); does not undo manual Blender edits."""
    return call("history", asset_ref=asset_ref)


@mcp.tool(annotations=annotation(replay=True))
def card_restore(asset_ref: str, expected_revision: int, revision: int, request_id: str,
                 parameters: list[str] | None = None) -> CallToolResult:
    """Restore a previous recipe or selected parameter names as a new revision."""
    return call("restore", asset_ref=asset_ref, expected_revision=expected_revision,
                revision=revision, request_id=request_id, parameters=parameters)


@mcp.tool(annotations=annotation())
def card_preview(asset_ref: str, view: Literal["front", "back", "edge", "perspective"] = "front",
                 resolution: int = 768) -> CallToolResult:
    """Render one standard view (128–1024 pixels). Returns PNG image and artifact path."""
    result = call("preview", asset_ref=asset_ref, view=view, resolution=resolution)
    if not result.isError:
        try:
            path = Path(result.structuredContent["path"])
            if path.suffix.lower() != ".png" or path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError("Invalid preview file")
            result.content.append(ImageContent(type="image", mimeType="image/png",
                                               data=base64.b64encode(path.read_bytes()).decode()))
        except (OSError, ValueError, KeyError) as exc:
            detail = DomainError("PREVIEW_READ_FAILED", str(exc)).result()
            return CallToolResult(isError=True, content=[TextContent(type="text", text=canonical(detail))],
                                  structuredContent=detail)
    return result


@mcp.tool(annotations=annotation())
def card_save(expected_filepath: str, filename: str | None = None) -> CallToolResult:
    """Save the complete CURRENT Blender project, like Ctrl+S. Copy project.filepath from status (empty if unsaved).

    Supply filename only for the first save of an unsaved project. Later saves update the same file with a Blender backup.
    """
    return call("save", expected_filepath=expected_filepath, filename=filename)


@mcp.tool(annotations=annotation())
def card_export(asset_ref: str, filename: str) -> CallToolResult:
    """Export an explicitly requested separate card-only copy. Does NOT save/update the live project. Never overwrites."""
    return call("export", asset_ref=asset_ref, filename=filename)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

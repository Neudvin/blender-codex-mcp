import asyncio
from collections import Counter
import importlib.util
import json
from pathlib import Path
import socket
import struct
import threading
import time
import zipfile

import pytest

from blender_codex_mcp.agentic import wire
from blender_codex_mcp.agentic.bridge import Bridge
from blender_codex_mcp.agentic.model import DomainError, inside_convex, outline, prism, validate_spec


@pytest.mark.parametrize("spec", [{"width_mm": True}, {"width_mm": float("nan")},
                                    {"width_mm": 0}, {"unknown": 1}, {"border_mm": 10, "height_mm": 20},
                                    {"texts": [{"id": "a", "text": "x"}, {"id": "a", "text": "y"}]}])
def test_invalid_specs(spec):
    with pytest.raises(DomainError):
        validate_spec(spec)


@pytest.mark.parametrize("cut", [0, 12])
def test_prism_watertight_and_winding(cut):
    points = outline(85, 55, cut)
    vertices, faces = prism(points, -0.4, 0.4)
    edges = Counter((f[i], f[(i + 1) % len(f)]) for f in faces for i in range(len(f)))
    assert all(count == 1 and edges[(b, a)] == 1 for (a, b), count in edges.items())
    assert max(v[0] for v in vertices) == pytest.approx(0.0425)
    assert inside_convex((0, 0), points, 1)
    if cut:
        assert not inside_convex((42, -27), points)


def test_fragmented_unicode_frame():
    value = {"text": "Crème — Café"}
    encoded = wire.pack(value)
    buffer = bytearray()
    for byte in encoded[:-1]:
        buffer.append(byte)
        assert wire.unpack(buffer) is None
    buffer.append(encoded[-1])
    assert wire.unpack(buffer) == value
    assert buffer == b""


@pytest.mark.parametrize("payload", [b"[]", b'{"v":NaN}', b"\xff", b"null", b"{"])
def test_invalid_frames(payload):
    with pytest.raises(DomainError):
        wire.unpack(bytearray(struct.pack("!I", len(payload)) + payload))


def test_frame_limits():
    with pytest.raises(DomainError):
        wire.unpack(bytearray(struct.pack("!I", wire.MAX_FRAME + 1)))
    with pytest.raises(DomainError):
        wire.pack({"value": "x" * wire.MAX_FRAME})


def test_bridge_real_socket_auth_and_fragmentation(tmp_path, monkeypatch):
    monkeypatch.setattr(wire, "token_path", lambda: tmp_path / "token")
    calls = []
    class Runtime:
        def dispatch(self, op, args):
            calls.append((op, args, threading.get_ident()))
            return {"ok": True, "echo": args}
    bridge = Bridge(Runtime(), port=0)
    port = bridge.socket.getsockname()[1]
    try:
        for token, expected in [("wrong", False), (wire.read_token(), True)]:
            with socket.create_connection(("127.0.0.1", port)) as sock:
                sock.settimeout(1)
                request = wire.pack({"protocol": 1, "id": "req", "token": token,
                                     "op": "status", "args": {"n": 3}})
                for fragment in [request[:2], request[2:7], request[7:]]:
                    sock.sendall(fragment)
                    bridge.tick()
                bridge.tick()
                result = wire.unpack(bytearray(sock.recv(65536)))
                assert result["result"]["ok"] is expected
                if not expected:
                    assert result["result"]["error"]["code"] == "UNAUTHORIZED"
        assert calls == [("status", {"n": 3}, threading.get_ident())]
    finally:
        bridge.close()


def test_mcp_schema_and_text_patch(monkeypatch):
    from blender_codex_mcp import agentic_server as server
    calls = []
    def call(op, args):
        calls.append((op, args))
        return {"ok": True}
    monkeypatch.setattr(server.client, "call", call)
    async def check():
        tools = await server.mcp.list_tools()
        assert len(tools) == 9
        assert all("execute" not in t.name for t in tools)
        text_tool = next(t for t in tools if t.name == "card_text_set")
        assert "TextPatch" in text_tool.inputSchema["$defs"]
        assert text_tool.inputSchema["$defs"]["TextPatch"]["additionalProperties"] is False
        result = await server.mcp.call_tool("card_text_set", {
            "asset_ref": "card:test", "expected_revision": 1, "request_id": "edit-1",
            "text": {"id": "name", "text": "NEW NAME"}})
        assert not result.isError
        assert calls[-1][1]["text"] == {"id": "name", "text": "NEW NAME"}
    asyncio.run(check())


def test_mcp_errors_are_structured(monkeypatch):
    from blender_codex_mcp import agentic_server as server
    def fail(*_):
        raise DomainError("NOT_CONNECTED", "Start add-on")
    monkeypatch.setattr(server.client, "call", fail)
    result = server.card_status()
    assert result.isError and result.structuredContent["error"]["code"] == "NOT_CONNECTED"


def test_addon_build_reproducible(tmp_path):
    path = Path(__file__).resolve().parents[1] / "scripts/build_agentic_addon.py"
    spec = importlib.util.spec_from_file_location("build", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    a = module.build(tmp_path / "a.zip")
    b = module.build(tmp_path / "b.zip")
    assert a.read_bytes() == b.read_bytes()
    with zipfile.ZipFile(a) as archive:
        assert "blender_agentic_mcp/agentic/runtime.py" in archive.namelist()
        assert not any("server.py" in name for name in archive.namelist())

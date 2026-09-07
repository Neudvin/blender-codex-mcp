"""Optional real-process integration: BLENDER_BIN=/path/to/blender pytest -q this_file."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import zipfile

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not os.environ.get("BLENDER_BIN"), reason="Set BLENDER_BIN for real Blender integration")
def test_packaged_addon_through_stdio(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "scripts/build_agentic_addon.py")], check=True)
    with zipfile.ZipFile(ROOT / "dist/blender_agentic_mcp.zip") as archive:
        archive.extractall(tmp_path / "addons")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    (tmp_path / "port").write_text(str(port))
    with (tmp_path / "blender.log").open("w+") as log:
        blender = subprocess.Popen([os.environ["BLENDER_BIN"], "--background", "--factory-startup",
                                    "--python-exit-code", "1", "--python", str(ROOT / "tests/blender_bridge_host.py"),
                                    "--", str(tmp_path)], stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 30
            while not (tmp_path / "ready").exists():
                assert blender.poll() is None, (tmp_path / "blender.log").read_text()
                assert time.monotonic() < deadline, "Blender startup timeout"
                time.sleep(0.05)

            async def conversation():
                params = StdioServerParameters(command=sys.executable,
                    args=["-m", "blender_codex_mcp.agentic_server"],
                    env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "BLENDER_AGENTIC_PORT": str(port)})
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        assert len((await session.list_tools()).tools) == 11
                        async def call(name, args):
                            result = await session.call_tool(name, args)
                            assert not result.isError, result
                            return result.structuredContent
                        assert (await call("card_status", {}))["execution_mode"] == "headless"
                        created = await call("card_create", {"request_id": "stdio-create"})
                        ref = created["asset_ref"]
                        edited = await call("card_text_set", {"asset_ref": ref, "expected_revision": 1,
                            "request_id": "stdio-edit", "text": {"id": "name", "text": "EXAMPLE NAME"}})
                        assert edited["revision"] == 2
                        preview = await session.call_tool("card_preview", {"asset_ref": ref, "resolution": 128})
                        assert not preview.isError
                        assert any(c.type == "image" and c.mimeType == "image/png" for c in preview.content)
                        status = await call("card_status", {})
                        saved = await call("card_save", {"expected_filepath": status["project"]["filepath"], "filename": "stdio-project.blend"})
                        assert Path(saved["path"]).is_file()
                        status = await call("card_status", {})
                        assert status["project"]["filepath"] == saved["path"]
                        assert not status["project"]["disk_changed"]
                        await call("card_update", {"asset_ref": ref, "expected_revision": 2,
                            "request_id": "stdio-veneer", "changes": {"veneer_mm": 0.5, "core_mm": 0.7}})
                        again = await call("card_save", {"expected_filepath": saved["path"]})
                        assert again["path"] == saved["path"] and not again["first_save"]
                        assert len((await call("card_status", {}))["assets"]) == 1
                        error = await session.call_tool("card_update", {"asset_ref": ref,
                            "expected_revision": 1, "request_id": "stdio-stale", "changes": {"width_mm": 90}})
                        assert error.isError and error.structuredContent["error"]["code"] == "STALE_REVISION"
            asyncio.run(conversation())
        finally:
            (tmp_path / "stop").touch()
            try:
                blender.wait(timeout=10)
            except subprocess.TimeoutExpired:
                blender.terminate()
                blender.wait(timeout=10)
        assert blender.returncode == 0, (tmp_path / "blender.log").read_text()
        assert "PACKAGED_ADDON_PASS" in (tmp_path / "blender.log").read_text()

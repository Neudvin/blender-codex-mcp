"""Bounded, length-prefixed JSON on loopback. No executable payloads."""
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import threading
import uuid

from .model import DomainError, canonical

MAX_FRAME = 1024 * 1024
PROTOCOL = 1


def token_path():
    return Path.home() / ".blender-agentic-mcp" / "bridge-token"


def read_token(create=False):
    path = token_path()
    if create:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "w") as f:
                f.write(secrets.token_hex(32))
    try:
        token = path.read_text().strip()
    except OSError as exc:
        raise DomainError("NOT_CONNECTED", "Start the Blender Agentic MCP add-on first.") from exc
    if len(token) != 64 or any(c not in "0123456789abcdef" for c in token):
        raise DomainError("INVALID_TOKEN_FILE", "Bridge token file is invalid; inspect local setup.")
    return token


def pack(value):
    raw = canonical(value).encode("utf-8")
    if len(raw) > MAX_FRAME:
        raise DomainError("MESSAGE_TOO_LARGE", "Request or response exceeds 1 MiB.")
    return struct.pack("!I", len(raw)) + raw


def unpack(buffer):
    if len(buffer) < 4:
        return None
    size = struct.unpack("!I", buffer[:4])[0]
    if size > MAX_FRAME or size == 0:
        raise DomainError("INVALID_FRAME", "Frame size must be 1 byte to 1 MiB.")
    if len(buffer) < size + 4:
        return None
    payload = bytes(buffer[4:4 + size])
    del buffer[:4 + size]
    try:
        result = json.loads(payload.decode("utf-8"), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON")))
    except (UnicodeError, ValueError) as exc:
        raise DomainError("INVALID_FRAME", "Invalid UTF-8 JSON frame.") from exc
    if not isinstance(result, dict):
        raise DomainError("INVALID_FRAME", "A frame must be a JSON object.")
    return result


class Client:
    def __init__(self, port=9877, timeout=180):
        self.port, self.timeout = port, timeout
        self.lock = threading.Lock()

    def call(self, op, args):
        request_id = uuid.uuid4().hex
        request = {"protocol": PROTOCOL, "id": request_id, "token": read_token(), "op": op, "args": args}
        # One bounded request per connection. No automatic replay after a timeout.
        with self.lock:
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=self.timeout) as sock:
                    sock.sendall(pack(request))
                    buffer = bytearray()
                    while True:
                        chunk = sock.recv(65536)
                        if not chunk:
                            raise DomainError("OUTCOME_UNKNOWN", "Connection closed. Inspect before retrying a mutation with the SAME request_id.")
                        buffer.extend(chunk)
                        response = unpack(buffer)
                        if response is not None:
                            if response.get("id") != request_id or response.get("protocol") != PROTOCOL:
                                raise DomainError("PROTOCOL_MISMATCH", "Bridge response identity/version mismatch.")
                            if buffer or not isinstance(response.get("result"), dict):
                                raise DomainError("INVALID_FRAME", "Expected one object result.")
                            return response["result"]
            except (OSError, TimeoutError) as exc:
                raise DomainError("OUTCOME_UNKNOWN", "Blender may still be executing. Inspect before retrying a mutation with the SAME request_id.") from exc

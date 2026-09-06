"""Nonblocking main-thread socket pump; no background Blender Python threads."""
import secrets
import socket
import time

from .model import DomainError
from .wire import MAX_FRAME, PROTOCOL, pack, read_token, unpack


class Bridge:
    def __init__(self, runtime, port=9877):
        self.runtime = runtime
        self.token = read_token(create=True)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.bind(("127.0.0.1", port))
            self.socket.listen(8)
            self.socket.setblocking(False)
        except Exception:
            self.socket.close()
            raise
        self.clients = {}

    def close(self):
        for sock in list(self.clients):
            self.drop(sock)
        self.socket.close()

    def drop(self, sock):
        self.clients.pop(sock, None)
        sock.close()

    def tick(self):
        # Bound socket work each tick; dispatch at most one Blender operation.
        try:
            sock, _ = self.socket.accept()
            sock.setblocking(False)
            if len(self.clients) >= 8:
                sock.close()
            else:
                self.clients[sock] = {"input": bytearray(), "output": bytearray(), "start": time.monotonic(), "done": False}
        except BlockingIOError:
            pass
        dispatched = False
        for sock, state in list(self.clients.items()):
            try:
                if time.monotonic() - state["start"] > 240:
                    self.drop(sock)
                    continue
                if state["output"]:
                    sent = sock.send(state["output"][:65536])
                    del state["output"][:sent]
                    if not state["output"]:
                        self.drop(sock)
                    continue
                if dispatched:
                    continue
                data = sock.recv(65536)
                if not data:
                    self.drop(sock)
                    continue
                state["input"].extend(data)
                if len(state["input"]) > MAX_FRAME + 4:
                    self.drop(sock)
                    continue
                request = unpack(state["input"])
                if request is None:
                    continue
                dispatched = True
                if state["input"]:
                    raise DomainError("INVALID_FRAME", "Only one request is allowed per connection.")
                if request.get("protocol") != PROTOCOL:
                    result = DomainError("PROTOCOL_MISMATCH", "Update server and add-on together.").result()
                elif not isinstance(request.get("token"), str) or not secrets.compare_digest(request["token"], self.token):
                    result = DomainError("UNAUTHORIZED", "Bridge authentication failed.").result()
                elif not isinstance(request.get("args"), dict) or not isinstance(request.get("op"), str):
                    result = DomainError("INVALID_ARGUMENT", "Expected operation and arguments.").result()
                else:
                    result = self.runtime.dispatch(request["op"], request["args"])
                state["output"] = bytearray(pack({"protocol": PROTOCOL, "id": request.get("id"), "result": result}))
            except BlockingIOError:
                pass
            except (OSError, DomainError):
                self.drop(sock)
        return 0.025

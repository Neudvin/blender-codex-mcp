"""Portable contracts and geometry; shared by MCP and the Blender add-on."""
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
import re
from typing import Literal, Optional


class DomainError(Exception):
    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code, self.details = code, details

    def result(self):
        return {"ok": False, "error": {"code": self.code, "message": str(self), **self.details}}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def number(value, label, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise DomainError("INVALID_ARGUMENT", f"{label} must be between {low} and {high}.")
    return float(value)


def identifier(value, label="id"):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value):
        raise DomainError("INVALID_ARGUMENT", f"{label} must contain 1–64 letters, digits, underscores or hyphens.")
    return value


@dataclass
class TextSpec:
    __pydantic_config__ = {"extra": "forbid"}
    id: str
    text: str
    side: Literal["front", "back"] = "front"
    x_mm: float = 0
    y_mm: float = 0
    size_mm: float = 2.4
    tracking: float = 1.1


def default_texts():
    return [TextSpec("name", "YOUR NAME"),
            TextSpec("address", "YOUR ADDRESS", "back", y_mm=12, size_mm=2),
            TextSpec("city", "CITY, REGION", "back", y_mm=7, size_mm=2),
            TextSpec("phone", "+1 000 000 0000", "back", y_mm=-5, size_mm=2),
            TextSpec("email", "NAME@EXAMPLE.COM", "back", y_mm=-10, size_mm=2)]


@dataclass
class CardSpec:
    __pydantic_config__ = {"extra": "forbid"}
    # Prototype dimensions, not measurements inferred from the photograph.
    width_mm: float = 85
    height_mm: float = 55
    core_mm: float = 0.8
    veneer_mm: float = 0.3
    border_mm: float = 0.8
    corner_cut_mm: float = 12
    bevel_mm: float = 0.08
    wood_color: list[float] = field(default_factory=lambda: [0.018, 0.022, 0.027])
    gold_color: list[float] = field(default_factory=lambda: [0.83, 0.58, 0.20])
    wood_roughness: float = 0.6
    gold_roughness: float = 0.23
    grain_angle_deg: float = 0
    font_path: str = ""
    texts: list[TextSpec] = field(default_factory=default_texts)


@dataclass
class CardPatch:
    __pydantic_config__ = {"extra": "forbid"}
    width_mm: Optional[float] = None
    height_mm: Optional[float] = None
    core_mm: Optional[float] = None
    veneer_mm: Optional[float] = None
    border_mm: Optional[float] = None
    corner_cut_mm: Optional[float] = None
    bevel_mm: Optional[float] = None
    wood_color: Optional[list[float]] = None
    gold_color: Optional[list[float]] = None
    wood_roughness: Optional[float] = None
    gold_roughness: Optional[float] = None
    grain_angle_deg: Optional[float] = None
    font_path: Optional[str] = None


@dataclass
class TextPatch:
    __pydantic_config__ = {"extra": "forbid"}
    id: str
    text: Optional[str] = None
    side: Optional[Literal["front", "back"]] = None
    x_mm: Optional[float] = None
    y_mm: Optional[float] = None
    size_mm: Optional[float] = None
    tracking: Optional[float] = None


def validate_text(raw):
    if not isinstance(raw, dict) or set(raw) - set(TextSpec.__dataclass_fields__):
        raise DomainError("INVALID_ARGUMENT", "Unknown text fields.")
    try:
        t = asdict(TextSpec(**raw))
    except TypeError as exc:
        raise DomainError("INVALID_ARGUMENT", "Text requires id and text.") from exc
    identifier(t["id"], "text id")
    if not isinstance(t["text"], str) or not 1 <= len(t["text"]) <= 256 or any(ord(c) < 32 for c in t["text"]):
        raise DomainError("INVALID_ARGUMENT", "Text must be one line of 1–256 printable characters.")
    if t["side"] not in ("front", "back"):
        raise DomainError("INVALID_ARGUMENT", "Text side must be front or back.")
    for key, bounds in {"x_mm": (-250, 250), "y_mm": (-250, 250), "size_mm": (0.5, 15), "tracking": (0.5, 3)}.items():
        t[key] = number(t[key], key, *bounds)
    return t


def validate_spec(raw):
    if not isinstance(raw, dict) or set(raw) - set(CardSpec.__dataclass_fields__):
        raise DomainError("INVALID_ARGUMENT", "Unknown card fields.")
    s = asdict(CardSpec())
    s.update(raw)
    bounds = {"width_mm": (30, 250), "height_mm": (20, 160), "core_mm": (0.1, 5),
              "veneer_mm": (0.05, 3), "border_mm": (0.1, 10), "corner_cut_mm": (0, 50),
              "bevel_mm": (0, 0.5), "wood_roughness": (0, 1), "gold_roughness": (0, 1),
              "grain_angle_deg": (-180, 180)}
    for key, limits in bounds.items():
        s[key] = number(s[key], key, *limits)
    inner = min(s["width_mm"], s["height_mm"]) - 2 * s["border_mm"]
    if inner <= 4 or s["corner_cut_mm"] > inner / 2:
        raise DomainError("CONSTRAINT_FAILED", "Border/corner leaves insufficient veneer area.")
    if s["bevel_mm"] > min(s["core_mm"], s["veneer_mm"], s["border_mm"]) / 3:
        raise DomainError("CONSTRAINT_FAILED", "Bevel must be at most one third of the thinnest layer or border.")
    for key in ("wood_color", "gold_color"):
        if not isinstance(s[key], list) or len(s[key]) != 3:
            raise DomainError("INVALID_ARGUMENT", f"{key} must have three linear RGB components.")
        s[key] = [number(c, key, 0, 1) for c in s[key]]
    if not isinstance(s["font_path"], str) or len(s["font_path"]) > 1024:
        raise DomainError("INVALID_ARGUMENT", "font_path must be a local font path or empty.")
    if not isinstance(s["texts"], list) or not 1 <= len(s["texts"]) <= 20:
        raise DomainError("INVALID_ARGUMENT", "Provide 1–20 text fields.")
    s["texts"] = [validate_text(t) for t in s["texts"]]
    if len({t["id"] for t in s["texts"]}) != len(s["texts"]):
        raise DomainError("INVALID_ARGUMENT", "Text ids must be unique across both faces.")
    return s


def outline(width, height, cut=0):
    """Counterclockwise outline in millimetres; cut lower-right physical corner."""
    x, y = width / 2, height / 2
    if cut == 0:
        return [(-x, -y), (x, -y), (x, y), (-x, y)]
    return [(-x, -y), (x - cut, -y), (x, -y + cut), (x, y), (-x, y)]


def prism(points, bottom_mm, top_mm):
    n = len(points)
    vertices = [(x / 1000, y / 1000, z / 1000) for z in (bottom_mm, top_mm) for x, y in points]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    return vertices, faces


def inside_convex(point, polygon, margin=0):
    x, y = point
    for i, (ax, ay) in enumerate(polygon):
        bx, by = polygon[(i + 1) % len(polygon)]
        if (bx - ax) * (y - ay) - (by - ay) * (x - ax) < margin * math.hypot(bx - ax, by - ay):
            return False
    return True

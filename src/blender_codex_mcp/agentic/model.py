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
    rotation_deg: float = 0


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
    construction: Literal["layered", "recessed"] = "layered"
    recess_mm: float = 0
    corner_radius_mm: float = 0
    total_thickness_mm: Optional[float] = None
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
    construction: Optional[Literal["layered", "recessed"]] = None
    recess_mm: Optional[float] = None
    corner_radius_mm: Optional[float] = None
    total_thickness_mm: Optional[float] = None
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
    rotation_deg: Optional[float] = None


@dataclass
class NativeCardObjects:
    __pydantic_config__ = {"extra": "forbid"}
    body: str
    front_veneer: str
    back_veneer: str
    web: str
    texts: list[str] = field(default_factory=list)


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
    for key, bounds in {"x_mm": (-250, 250), "y_mm": (-250, 250), "size_mm": (0.5, 15), "tracking": (0.5, 3), "rotation_deg": (-360, 360)}.items():
        t[key] = number(t[key], key, *bounds)
    return t


def validate_spec(raw):
    if not isinstance(raw, dict) or set(raw) - set(CardSpec.__dataclass_fields__):
        raise DomainError("INVALID_ARGUMENT", "Unknown card fields.")
    s = asdict(CardSpec())
    s.update(raw)
    if s["total_thickness_mm"] is not None:
        total = number(s["total_thickness_mm"], "total_thickness_mm", 0.1, 11)
        veneer = number(s["veneer_mm"], "veneer_mm", 0, 3)
        s["core_mm"] = total - 2 * veneer
    # Total is an input convenience, not a second persistent source of thickness.
    s["total_thickness_mm"] = None
    bounds = {"width_mm": (30, 250), "height_mm": (20, 160), "core_mm": (0.1, 5),
              "veneer_mm": (0, 3), "border_mm": (0.1, 10), "corner_cut_mm": (0, 50),
              "recess_mm": (0, 2), "corner_radius_mm": (0, 20),
              "bevel_mm": (0, 0.5), "wood_roughness": (0, 1), "gold_roughness": (0, 1),
              "grain_angle_deg": (-180, 180)}
    for key, limits in bounds.items():
        s[key] = number(s[key], key, *limits)
    inner = min(s["width_mm"], s["height_mm"]) - 2 * s["border_mm"]
    if inner <= 4 or s["corner_cut_mm"] > inner / 2:
        raise DomainError("CONSTRAINT_FAILED", "Border/corner leaves insufficient veneer area.")
    if s["construction"] not in ("layered", "recessed"):
        raise DomainError("INVALID_ARGUMENT", "construction must be layered or recessed.")
    if s["recess_mm"] and s["construction"] != "recessed":
        raise DomainError("CONSTRAINT_FAILED", "recess_mm requires recessed construction.")
    if s["construction"] == "recessed" and (s["veneer_mm"] <= 0 or s["core_mm"] - 2 * s["recess_mm"] < 0.1):
        raise DomainError("CONSTRAINT_FAILED", "Recessed cards require veneers and at least 0.1 mm of center web.")
    if s["corner_radius_mm"] > min(s["width_mm"], s["height_mm"]) / 2:
        raise DomainError("CONSTRAINT_FAILED", "Corner radius exceeds half the card's smaller dimension.")
    if s["corner_radius_mm"] and s["corner_cut_mm"]:
        raise DomainError("CONSTRAINT_FAILED", "Choose rounded corners or a diagonal cut for this recipe.")
    thin = [s["core_mm"] - 2 * s["recess_mm"], s["border_mm"]]
    if s["veneer_mm"]: thin.append(s["veneer_mm"])
    if s["bevel_mm"] > min(thin) / 3:
        raise DomainError("CONSTRAINT_FAILED", "Bevel must be at most one third of the thinnest layer or border.")
    for key in ("wood_color", "gold_color"):
        if not isinstance(s[key], list) or len(s[key]) != 3:
            raise DomainError("INVALID_ARGUMENT", f"{key} must have three linear RGB components.")
        s[key] = [number(c, key, 0, 1) for c in s[key]]
    if not isinstance(s["font_path"], str) or len(s["font_path"]) > 1024:
        raise DomainError("INVALID_ARGUMENT", "font_path must be a local font path or empty.")
    if not isinstance(s["texts"], list) or not 0 <= len(s["texts"]) <= 20:
        raise DomainError("INVALID_ARGUMENT", "Provide 0–20 text fields; an empty list makes a blank card.")
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


def rounded_outline(width, height, radius, segments=12):
    if not radius:
        return outline(width, height)
    pts=[]
    for cx,cy,start in [(width/2-radius,-height/2+radius,-90),
                        (width/2-radius,height/2-radius,0),
                        (-width/2+radius,height/2-radius,90),
                        (-width/2+radius,-height/2+radius,180)]:
        for j in range(segments+1):
            a=math.radians(start+j*90/segments)
            pts.append((cx+radius*math.cos(a),cy+radius*math.sin(a)))
    return pts


def card_face(spec):
    if not spec['veneer_mm']:
        return rounded_outline(spec['width_mm'],spec['height_mm'],spec['corner_radius_mm'])
    w,h=spec['width_mm']-2*spec['border_mm'],spec['height_mm']-2*spec['border_mm']
    if spec['corner_radius_mm']:
        return rounded_outline(w,h,max(0,spec['corner_radius_mm']-spec['border_mm']))
    return outline(w,h,spec['corner_cut_mm'])


def convex_hull(points):
    points=sorted(set(tuple(p) for p in points))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[]
    for p in points:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=1e-10:lower.pop()
        lower.append(p)
    upper=[]
    for p in reversed(points):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=1e-10:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]


def frame_mesh(outer, inner, low, high):
    """Manifold prism with a convex hole. Triangulate the annulus by angular sweep."""
    # Recipes generated by this package use matching loops.  Quads avoid the
    # tiny sliver/seam triangles that a generic angular sweep can introduce.
    if len(outer) == len(inner):
        n = len(outer)
        vertices = [(x / 1000, y / 1000, z / 1000) for z in (low, high)
                    for loop in (outer, inner) for x, y in loop]
        k = 2 * n
        faces = []
        for i in range(n):
            j = (i + 1) % n
            # top/bottom annulus, then outside and inside walls
            faces.append((k + i, k + j, k + n + j))
            faces.append((k + i, k + n + j, k + n + i))
            faces.append((j, i, n + i))
            faces.append((j, n + i, n + j))
            faces.append((i, j, k + j, k + i))
            faces.append((n + j, n + i, k + n + i, k + n + j))
        return vertices, faces
    # Join the two CCW loops by advancing whichever next polar angle comes first.
    def sorted_loop(loop):return sorted(loop,key=lambda p:math.atan2(p[1],p[0]))
    outer,inner=sorted_loop(outer),sorted_loop(inner)
    n,m=len(outer),len(inner)
    planar=outer+inner
    vertices=[(x/1000,y/1000,z/1000) for z in (low,high) for x,y in planar]
    k=n+m
    faces=[]
    angles_o=[math.atan2(y,x) for x,y in outer]+[math.atan2(outer[0][1],outer[0][0])+2*math.pi]
    angles_i=[math.atan2(y,x) for x,y in inner]+[math.atan2(inner[0][1],inner[0][0])+2*math.pi]
    a=b=0
    while a<n or b<m:
        if b==m or (a<n and angles_o[a+1]<=angles_i[b+1]):
            face=(a%n,(a+1)%n,n+b%m);a+=1
        else:
            face=(a%n,n+(b+1)%m,n+b%m);b+=1
        faces.append(tuple(v+k for v in face));faces.append(tuple(reversed(face)))
    for i in range(n):faces.append((i,(i+1)%n,(i+1)%n+k,i+k))
    for i in range(m):faces.append((n+(i+1)%m,n+i,n+i+k,n+(i+1)%m+k))
    return vertices,faces

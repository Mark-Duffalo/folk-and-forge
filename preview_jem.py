"""Offline preview of a CEM .jem model with its textures (no game needed).

Renders the rest pose the way EMF does: top-level parts at their `translate` pivot (run
normalize_jem.py first so those are vanilla), static rotations applied, first-level submodel
translates absolute, deeper ones relative. Texture layers (base skin, then biome / profession /
level overlays) are drawn on the same geometry, like the game's villager overlay layers.

Usage: python preview_jem.py model.jem out.png base.png [overlay.png ...] [--yaw 30] [--pitch 12]
"""
import json, math, sys
from PIL import Image, ImageDraw


def rot(deg):
    cx, cy, cz = (math.cos(math.radians(a)) for a in deg)
    sx, sy, sz = (math.sin(math.radians(a)) for a in deg)
    rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    return mul(rz, mul(ry, rx))


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def apply(frame, p):
    m, t = frame
    return [t[i] + sum(m[i][k] * p[k] for k in range(3)) for i in range(3)]


def compose(frame, offset, r):
    m, t = frame
    return (mul(m, r), apply(frame, offset))


def box_faces(box, frame, mirror, tex_size):
    x0, y0, z0, w, h, d = box["coordinates"]
    u, v = box.get("textureOffset", [0, 0])
    s = box.get("sizeAdd", 0)
    X0, Y0, Z0, X1, Y1, Z1 = x0 - s, y0 - s, z0 - s, x0 + w + s, y0 + h + s, z0 + d + s
    # (texture rect, top-left corner, U edge, V edge); +x = entity's right = screen-left from the front
    right = ((u, v + d, d, h), (X1, Y1, Z1), (0, 0, Z0 - Z1), (0, Y0 - Y1, 0))
    left = ((u + d + w, v + d, d, h), (X0, Y1, Z0), (0, 0, Z1 - Z0), (0, Y0 - Y1, 0))
    if mirror:
        right, left = (left[0],) + right[1:], (right[0],) + left[1:]
    faces = [
        ((u + d, v + d, w, h), (X1, Y1, Z0), (X0 - X1, 0, 0), (0, Y0 - Y1, 0)),          # front
        ((u + 2 * d + w, v + d, w, h), (X0, Y1, Z1), (X1 - X0, 0, 0), (0, Y0 - Y1, 0)),  # back
        right, left,
        ((u + d, v, w, d), (X1, Y1, Z1), (X0 - X1, 0, 0), (0, 0, Z0 - Z1)),              # top
        ((u + d + w, v, w, d), (X1, Y0, Z0), (X0 - X1, 0, 0), (0, 0, Z1 - Z0)),          # bottom
    ]
    out = []
    for rect, o, U, V in faces:
        if mirror:
            o, U = tuple(a + b for a, b in zip(o, U)), tuple(-a for a in U)
        p0 = apply(frame, o)
        pu = [a - b for a, b in zip(apply(frame, [o[i] + U[i] for i in range(3)]), p0)]
        pv = [a - b for a, b in zip(apply(frame, [o[i] + V[i] for i in range(3)]), p0)]
        out.append((rect, p0, pu, pv, tex_size))
    return out


HEAD_GROUP = ("head", "nose", "headwear", "headwear2")


def model_faces(jem, head_rot=None):
    """head_rot: optional [rx, ry, rz] degrees, turns the head group about the head pivot like the game."""
    tex_size = jem.get("textureSize", [64, 64])
    faces = []
    head = next((m for m in jem["models"] if m.get("part") == "head"), None)
    ph = [-a for a in head.get("translate", [0, 0, 0])] if head else [0, 0, 0]
    rh = rot(head_rot) if head_rot else None

    def walk(part, frame, depth, parent_t, inherited_mirror):
        mirror = inherited_mirror or "u" in part.get("mirrorTexture", "")
        ts = part.get("textureSize", tex_size)
        t = part.get("translate", [0, 0, 0])
        r = rot(part.get("rotate", [0, 0, 0]))
        if depth == 0:
            f = (r, [-a for a in t])                        # pivot = -translate
            box_off = t                                     # top-level boxes are absolute
            if rh and part.get("part") in HEAD_GROUP:       # child of the head in the game
                rel = [f[1][i] - ph[i] for i in range(3)]
                f = (mul(rh, r), [ph[i] + sum(rh[i][k] * rel[k] for k in range(3)) for i in range(3)])
        else:
            off = [a + b for a, b in zip(t, parent_t)] if depth == 1 else t
            f = compose(frame, off, r)
            box_off = [0, 0, 0]
        for b in part.get("boxes", []):
            bb = dict(b)
            c = list(b["coordinates"])
            bb["coordinates"] = [c[0] + box_off[0], c[1] + box_off[1], c[2] + box_off[2]] + c[3:]
            faces.extend(box_faces(bb, f, mirror, ts))
        for sub in part.get("submodels", []):
            walk(sub, f, depth + 1, t, mirror)

    for part in jem["models"]:
        walk(part, None, 0, None, False)
    return faces


def render(jem, layers, yaw=30, pitch=12, scale=14, size=(420, 560), head_rot=None, shade=False):
    """shade=True lights faces like the game does (tops brightest, sides darker) for nicer pictures."""
    view = mul(rot([-pitch, 0, 0]), rot([0, -yaw, 0]))
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size[0] / 2, size[1] - 40

    def proj(p):
        q = [sum(view[i][k] * p[k] for k in range(3)) for i in range(3)]
        return (cx - q[0] * scale, cy - q[1] * scale, q[2])

    drawn = []
    for rect, p0, pu, pv, ts in model_faces(jem, head_rot):
        a, b, c = proj(p0), proj([p0[i] + pu[i] for i in range(3)]), proj([p0[i] + pv[i] for i in range(3)])
        # outward normal = -(U x V); visible if it points toward the camera (screen z < 0)
        nz = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if nz <= 0:
            continue
        depth = a[2] + (b[2] - a[2]) / 2 + (c[2] - a[2]) / 2
        light = 1.0
        if shade:   # world-space outward normal -(U x V), light from above and slightly in front
            n = [-(pu[1] * pv[2] - pu[2] * pv[1]), -(pu[2] * pv[0] - pu[0] * pv[2]), -(pu[0] * pv[1] - pu[1] * pv[0])]
            ln = math.sqrt(sum(x * x for x in n)) or 1
            L = (0.25, 0.85, -0.47)
            light = 0.58 + 0.42 * max(0.0, sum(n[i] / ln * L[i] for i in range(3)))
        drawn.append((depth, rect, a, b, c, ts, light))
    drawn.sort(key=lambda f: -f[0])
    for _, (tu, tv, tw, th), a, b, c, ts, light in drawn:
        if tw <= 0 or th <= 0:
            continue
        for layer in layers:
            kx, ky = layer.width / ts[0], layer.height / ts[1]
            for j in range(int(th)):
                for i in range(int(tw)):
                    px = layer.getpixel((min(int((tu + i) * kx), layer.width - 1), min(int((tv + j) * ky), layer.height - 1)))
                    if px[3] < 128:
                        continue
                    pts = []
                    for di, dj in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                        fu, fv = di / tw, dj / th
                        pts.append((a[0] + (b[0] - a[0]) * fu + (c[0] - a[0]) * fv,
                                    a[1] + (b[1] - a[1]) * fu + (c[1] - a[1]) * fv))
                    draw.polygon(pts, fill=tuple(min(255, int(v * light)) for v in px[:3]) + (255,))
    return img


if __name__ == "__main__":
    args, opts = [], {"--yaw": 30, "--pitch": 12}
    it = iter(sys.argv[1:])
    for a in it:
        if a in opts:
            opts[a] = float(next(it))
        else:
            args.append(a)
    if len(args) < 3:
        sys.exit(__doc__)
    jem = json.load(open(args[0], encoding="utf-8"))
    layers = [Image.open(p).convert("RGBA") for p in args[2:]]
    render(jem, layers, opts["--yaw"], opts["--pitch"]).save(args[1])

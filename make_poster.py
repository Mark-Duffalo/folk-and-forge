"""Render the Folk & Forge poster: stacked logo over an in-game screenshot, villagers peeking around it.

    python make_poster.py [path/to/26.3.jar]        -> art/folk_and_forge_poster.png (1920x1080)

Layout: the background screenshot (BACKGROUND), a stacked logo near the top (stone "FOLK & FORGE",
an orange-gold "THE FOLKS UPDATE" line flanked by crossed hammers, all on one solid dark backing),
and the race villagers peeking over and around it. The backing hides their bodies, so they look
like they stand behind the sign. Villagers are rendered from the real pack files with preview_jem.py,
so re-run after art changes. Block textures come from your Minecraft jar.
Edit LINE1 / LINE2 / BACKGROUND / PEEKERS below.
"""
import io, json, os, sys, time, zipfile
from PIL import Image, ImageDraw, ImageFilter, ImageChops

JAR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.expandvars(r"%APPDATA%\.minecraft\versions\26.3\26.3.jar")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")
from preview_jem import render  # noqa: E402

W, H = 1920, 1080
LINE1 = "FOLK & FORGE"
LINE2 = "THE FOLKS UPDATE"
BACKGROUND = "art/background_hobbit_hole.png"
LOGO_TOP = 215                      # y of the logo's top edge
CEM = "server_resourcepack/assets/minecraft/optifine/cem/"
RND = "server_resourcepack/assets/minecraft/optifine/random/entity/villager/"
VAN = "jar:entity/villager/"
# Villagers behind the logo. where: "top" = head over the top edge at fraction x of the logo width,
# "left"/"right" = leaning out from that side at height fraction y. show = visible part of the render.
PEEKERS = [
    dict(where="top", x=0.10, model="villager8", layers=["villager8", "type/snow8", "profession/armorer8"], yaw=-15, show=0.52),
    dict(where="top", x=0.29, model="villager3", layers=["villager3", VAN + "type/plains.png", VAN + "profession/cleric.png"], yaw=-8, show=0.47),
    dict(where="top", x=0.50, model="villager4", layers=["villager4", "profession/librarian4"], yaw=0, show=0.52),
    dict(where="top", x=0.71, model="villager6", layers=["villager6", "profession/fisherman6"], yaw=8, show=0.5),
    dict(where="top", x=0.90, model="villager2", layers=["villager212", "type/plains2", "profession/farmer2"], yaw=15, show=0.52),
    dict(where="left", y=0.70, model="villager_baby8", layers=["villager_baby8"], yaw=-30, show=0.8, tilt=16),
    dict(where="right", y=0.50, model="villager7", layers=["villager7", "profession/mason7"], yaw=35, show=0.78, tilt=-16),
]

LETTERS = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "&": [".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"],
    " ": ["...", "...", "...", "...", "...", "...", "..."],
}


class Jar:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)

    def img(self, rel):
        return Image.open(io.BytesIO(self.z.read(f"assets/minecraft/textures/{rel}"))).convert("RGBA")


def shade(im, f):
    return Image.eval(im.convert("RGB"), lambda v: min(255, int(v * f))).convert("RGBA")


def tiled(tex, w, h, px):
    t = tex.resize((tex.width * px, tex.height * px), Image.NEAREST)
    out = Image.new("RGBA", (w, h))
    for yy in range(0, h, t.height):
        for xx in range(0, w, t.width):
            out.paste(t, (xx, yy))
    return out


def gradient(w, h, top, bottom):
    out = Image.new("RGBA", (w, h))
    for y in range(h):
        t = y / max(1, h - 1)
        out.paste(tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,), (0, y, w, y + 1))
    return out


def block_text(text, cell, face, under, depth, special=None):
    """Blocky letters: `face` image for the front, `under` for the extruded underside.
    special = {char: (face, under)} overrides for single characters (the gold ampersand)."""
    cols, x = [], 0
    for ch in text:
        cols.append((ch, x))
        x += len(LETTERS[ch][0]) + 1
    w, h = (x - 1) * cell, 7 * cell + depth
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    fill = lambda im: im if im.size == (w, h) else im.resize((w, h))
    groups = {}
    for ch, cx in cols:
        key = ch if special and ch in special else None
        m = groups.setdefault(key, Image.new("L", (w, h), 0))
        d = ImageDraw.Draw(m)
        for gy, row in enumerate(LETTERS[ch]):
            for gx, c in enumerate(row):
                if c == "#":
                    d.rectangle([(cx + gx) * cell, gy * cell, (cx + gx + 1) * cell - 1, (gy + 1) * cell - 1], fill=255)
    for key, m in groups.items():
        f, u = (special[key] if key else (face, under))
        body = Image.new("L", (w, h), 0)
        for k in range(depth + 1):
            body.paste(255, (0, k), mask=m.crop((0, 0, w, h - k)))
        out.paste(fill(u), (0, 0), body)
        out.paste(fill(f), (0, 0), m)
        # light on the top edge of every letter cell that has nothing above it
        top = ImageChops.subtract(m, m.transform(m.size, Image.AFFINE, (1, 0, 0, 0, 1, -max(2, cell // 8))))
        out.paste((255, 255, 255, 80), (0, 0), top)
    return out


def crossed_hammers(size):
    """Two crossed smithing hammers as pixel art (16x16 drawn, scaled to `size`)."""
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()
    wood, wood_d, iron, iron_d, iron_l = (150, 106, 60), (96, 64, 34), (196, 196, 202), (118, 118, 126), (238, 238, 244)
    for flip in (False, True):
        put = lambda x, y, c: px.__setitem__((15 - x if flip else x, y), c + (255,))
        for t in range(2, 13):                               # handle: bottom-left to top-right
            put(t, 15 - t, wood if t % 3 else wood_d)
        for dx, dy, c in [(-2, -1, iron_d), (-1, -1, iron), (0, -1, iron_l), (1, -1, iron_l), (-1, 0, iron), (0, 0, iron),
                          (1, 0, iron_l), (2, 0, iron_l), (0, 1, iron_d), (1, 1, iron), (2, 1, iron), (3, 1, iron_d),
                          (1, 2, iron_d), (2, 2, iron_d)]:
            put(12 + dx, 2 + dy, c)
    return im.resize((size, size), Image.NEAREST)


def logo(jar):
    stone, gold = jar.img("block/stone.png"), jar.img("block/gold_block.png")
    c1 = 22
    w1 = 67 * c1
    line1 = block_text(LINE1, c1, tiled(stone, w1, 7 * c1 + 14, 3), shade(tiled(stone, w1, 7 * c1 + 14, 3), 0.42), 14,
                       special={"&": (tiled(gold, w1, 7 * c1 + 14, 3), shade(tiled(gold, w1, 7 * c1 + 14, 3), 0.5))})
    c2 = 13
    line2 = block_text(LINE2, c2, gradient(1400, 7 * c2 + 10, (255, 226, 92), (236, 112, 26)),
                       gradient(1400, 7 * c2 + 10, (150, 60, 14), (110, 40, 10)), 10)
    hammers = crossed_hammers(7 * c2 + 40)
    gap = 26
    w = max(line1.width, line2.width + 2 * (hammers.width + gap))
    h = line1.height + 26 + line2.height
    pad = 40
    group = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    group.alpha_composite(line1, (pad + (w - line1.width) // 2, pad))
    y2 = pad + line1.height + 26
    x2 = pad + (w - line2.width) // 2
    group.alpha_composite(line2, (x2, y2))
    hy = y2 + (line2.height - hammers.height) // 2
    group.alpha_composite(hammers, (x2 - gap - hammers.width, hy))
    group.alpha_composite(hammers.transpose(Image.FLIP_LEFT_RIGHT), (x2 + line2.width + gap, hy))
    # one solid backing: outline the letters, then fill every row from its first to last pixel so
    # nothing behind the sign shows between letters or between the two lines
    shape = group.split()[3].point(lambda v: 255 if v else 0).filter(ImageFilter.MaxFilter(21))
    backing = Image.new("L", shape.size, 0)
    sp, bd = shape.load(), ImageDraw.Draw(backing)
    for y in range(shape.height):
        xs = [x for x in range(shape.width) if sp[x, y]]
        if xs:
            bd.line([(xs[0], y), (xs[-1], y)], fill=255)
    rim = backing.filter(ImageFilter.MaxFilter(7))
    out = Image.new("RGBA", group.size, (0, 0, 0, 0))
    out.paste((12, 10, 14, 255), (0, 0), rim)
    planks = shade(tiled(jar.img("block/dark_oak_planks.png"), out.width, out.height, 4), 0.62)   # a wooden signboard
    out.paste(planks, (0, 0), backing)
    out.alpha_composite(group)
    return out, backing


def villager(jar, p):
    jem = json.load(open(f"{CEM}{p['model']}.jem", encoding="utf-8"))
    imgs = [jar.img(l[4:]) if l.startswith("jar:") else Image.open(f"{RND}{l}.png").convert("RGBA") for l in p["layers"]]
    im = render(jem, imgs, p["yaw"], 4, scale=p.get("scale", 9.5), size=(520, 600), shade=True)
    im = im.crop(im.getbbox())
    if p.get("tilt"):
        im = im.rotate(p["tilt"], expand=True, resample=Image.NEAREST)
        im = im.crop(im.getbbox())
    return im


def main():
    jar = Jar(JAR)
    poster = Image.open(BACKGROUND).convert("RGBA").resize((W, H))
    lg, backing = logo(jar)
    lx, ly = (W - lg.width) // 2, LOGO_TOP
    for p in PEEKERS:                                        # behind the logo
        v = villager(jar, p)
        if p["where"] == "top":
            x = lx + int(p["x"] * lg.width)
            col = [backing.getpixel((min(lg.width - 1, max(0, x - lx)), y)) for y in range(lg.height)]
            edge = ly + next(y for y, a in enumerate(col) if a)
            poster.alpha_composite(v, (x - v.width // 2, edge - int(v.height * p["show"])))
        else:
            rows = [y for y in range(lg.height) if backing.getpixel((lg.width // 2, y))]
            y = ly + int(p["y"] * lg.height) - v.height // 2
            row = min(lg.height - 1, max(0, y - ly + v.height // 2))
            xs = [x for x in range(lg.width) if backing.getpixel((x, row))]
            if p["where"] == "left":
                poster.alpha_composite(v, (lx + xs[0] - int(v.width * p["show"]), y))
            else:
                poster.alpha_composite(v, (lx + xs[-1] - int(v.width * (1 - p["show"])), y))
    poster.alpha_composite(lg, (lx, ly))
    os.makedirs("art", exist_ok=True)
    out = "art/folk_and_forge_poster.png"
    poster.convert("RGB").save(out + ".tmp.png")
    for attempt in range(20):        # an image viewer may briefly lock the old poster
        try:
            os.replace(out + ".tmp.png", out)
            break
        except OSError:
            time.sleep(0.5)
    else:
        sys.exit(f"{out} is locked (close it in your image viewer); new poster left at {out}.tmp.png")
    print("art/folk_and_forge_poster.png")


if __name__ == "__main__":
    main()

"""Generate random look variants for every race and the ETF rules that pick between them.

ETF picks one base skin per villager from the list in random/entity/villager/villager.properties,
seeded by the villager's UUID, so each villager keeps its look. Overlays (biome / profession /
level) have their own rules and are shared by all variants of a race, and so is the model.

Run after build_dwarf.py (the dwarf variants start from its villager8.png):
    python build_variants.py [path/to/26.3.jar]
Variant numbers: race skin N keeps N for the original look; variants are N01, N02, ... (e.g. 201).

Recolors work on color masks, so they follow whatever you paint in the base skins:
  hair  - dark browns (hobbit: inside the head region only; dwarf: the generated hair palette)
  skin  - the villager skin-tone cluster
  eyes  - vanilla villager green
  scales/metal - each race's main hue band (see RACES below)
Copper stages are not random: each gets its own rule for the per-stage team the datapack sets.
"""
import colorsys, glob, io, itertools, os, sys, zipfile
from PIL import Image
import race_teams

JAR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.expandvars(r"%APPDATA%\.minecraft\versions\26.3\26.3.jar")
A = "server_resourcepack/assets/minecraft"
TEX, RAND = f"{A}/textures/entity/villager", f"{A}/optifine/random/entity/villager"
HDR = "# Matches the villager's scoreboard team (set by the races datapack). No names needed.\n"


def hsv(p):
    return colorsys.rgb_to_hsv(p[0] / 255, p[1] / 255, p[2] / 255)


def clamp(v):
    return max(0, min(255, int(round(v))))


def recolor(img, mask, target):
    """Move masked pixels so their mean becomes `target`, keeping each pixel's light/dark offset."""
    px = img.load()
    pts = [(x, y) for y in range(img.height) for x in range(img.width) if px[x, y][3] and mask(x, y, px[x, y])]
    if not pts:
        return img
    mean = [sum(px[p][i] for p in pts) / len(pts) for i in range(3)]
    for p in pts:
        r, g, b, a = px[p]
        px[p] = (clamp(target[0] + r - mean[0]), clamp(target[1] + g - mean[1]), clamp(target[2] + b - mean[2]), a)
    return img


def hue_shift(img, mask, shift=0.0, sat=1.0, val=1.0, val_add=0.0):
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            p = px[x, y]
            if p[3] and mask(x, y, p):
                h, s, v = hsv(p)
                r, g, b = colorsys.hsv_to_rgb((h + shift / 360) % 1, min(1, s * sat), min(1, v * val + val_add))
                px[x, y] = (clamp(r * 255), clamp(g * 255), clamp(b * 255), p[3])
    return img


def palette_map(img, mask, palette):
    """Replace masked pixels by the palette color at the same brightness rank (vanilla copper stages)."""
    px = img.load()
    pts = [(x, y) for y in range(img.height) for x in range(img.width) if px[x, y][3] and mask(x, y, px[x, y])]
    lum = lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
    pts.sort(key=lambda p: lum(px[p]))
    pal = sorted(palette, key=lum)
    for i, p in enumerate(pts):
        c = pal[int(i / max(1, len(pts) - 1) * (len(pal) - 1))]
        px[p] = c[:3] + (px[p][3],)
    return img


# ---- masks ---------------------------------------------------------------------------------
def is_skin(x, y, p):
    h, s, v = hsv(p)
    return 0.0 <= h <= 0.09 and 0.25 <= s <= 0.62 and v >= 0.5


def hobbit_hair(x, y, p):
    h, s, v = hsv(p)
    return x >= 64 and y < 18 and 0.05 <= h <= 0.12 and s >= 0.5 and v <= 0.4


DWARF_HAIR = {(122, 66, 32), (138, 76, 37), (104, 55, 26), (158, 92, 46), (88, 45, 20)}


def dwarf_hair(x, y, p):
    return tuple(p[:3]) in DWARF_HAIR


def green_eye(x, y, p):
    return p[1] > 110 and p[0] < 70 and p[2] < 70


def band(lo, hi, min_s):
    def m(x, y, p):
        h, s, v = hsv(p)
        return lo <= h * 360 <= hi and s >= min_s
    return m


# ---- accessories ---------------------------------------------------------------------------
def put(img, pts, color):
    px = img.load()
    for p in pts:
        if px[p][3]:
            px[p] = color + (255,)
    return img


def hobbit_freckles(img):
    px = img.load()
    dark = lambda p: tuple(clamp(c - 38) for c in px[p][:3])
    for p in [(73, 15), (72, 16), (78, 15), (79, 16), (74, 16), (77, 16)]:
        px[p] = dark(p) + (255,)
    return img


def elf_circlet(img):
    silver, gem = (205, 210, 222), (70, 140, 220)
    row = 10
    put(img, [(x, row) for x in range(0, 32)], silver)          # wraps sides, front and back of the head
    return put(img, [(11, row), (12, row)], gem)


def dwarf_scar(img):
    return put(img, [(13, 11), (13, 12), (14, 13)], (196, 118, 104))


def kobold_earrings(img):
    return put(img, [(x, 33) for x in range(52, 64)], (226, 178, 56))


def fishfolk_pearls(img):
    pearls = [(x, 88) for x in range(67, 95)]
    px = img.load()
    for i, p in enumerate(pearls):
        if px[p][3]:
            px[p] = ((242, 240, 232) if i % 2 == 0 else (206, 200, 190)) + (255,)
    return img


# ---- per-race variant recipes --------------------------------------------------------------
SKIN = {"base": None, "fair": (228, 178, 150), "deep": (118, 76, 54)}
HOBBIT_HAIR = {"base": None, "blonde": (196, 150, 74), "ginger": (150, 66, 26), "black": (34, 28, 26)}
DWARF_HAIRS = {"base": None, "black": (40, 32, 30), "blonde": (196, 152, 80), "grey": (168, 164, 158)}
# Light hair only appears with the lighter skin tones (hobbit and dwarf; elf variants are eye colors).
LIGHT_HAIR = {"blonde", "grey"}
DARK_SKIN = {"deep"}
ELF_EYES = {"base": None, "blue": (40, 110, 210), "violet": (136, 70, 196), "amber": (206, 146, 30)}


def humanoid(skin_n, hair_mask, hairs, accessory, eyes=None):
    """hair x skin x (with / without accessory). For the elf, `hairs` are eye colors."""
    out = []
    for (hk, hc), (sk, sc), acc in itertools.product(hairs.items(), SKIN.items(), (False, True)):
        if hk in LIGHT_HAIR and sk in DARK_SKIN:
            continue
        def make(img, hc=hc, sc=sc, acc=acc):
            if sc:
                recolor(img, is_skin, sc)
            if hc:
                recolor(img, hair_mask or green_eye, hc)
            return accessory(img) if acc else img
        out.append((f"{hk}/{sk}/{'acc' if acc else 'plain'}", make))
    return out


def copper(jar):
    def block_palette(name):
        im = Image.open(io.BytesIO(jar.read(f"assets/minecraft/textures/block/{name}.png"))).convert("RGBA")
        return [im.getpixel((x, y)) for x in range(16) for y in range(16)]
    mask = band(0, 26, 0.35)
    stages = [("exposed", block_palette("exposed_copper")), ("weathered", block_palette("weathered_copper")),
              ("oxidized", block_palette("oxidized_copper"))]
    mean = lambda pal: tuple(sum(c[i] for c in pal) / len(pal) for i in range(3))
    # exposed/weathered textures mix pink and green speckles, which look noisy on a model:
    # shift the construct's own shading to the stage's average color; oxidized is uniform, so map it.
    return [("base", lambda img: img),
            ("exposed", lambda img: recolor(img, mask, mean(stages[0][1]))),
            ("weathered", lambda img: recolor(img, mask, mean(stages[1][1]))),
            ("oxidized", lambda img: palette_map(img, mask, stages[2][1]))]


def scales(mask, schemes, accessory):
    out = []
    for (name, kw), acc in itertools.product(schemes, (False, True)):
        def make(img, kw=kw, acc=acc):
            if kw:
                hue_shift(img, mask, **kw)
            return accessory(img) if acc else img
        out.append((f"{name}/{'acc' if acc else 'plain'}", make))
    return out


# Fishfolk skin is the green band; the blue pants (170-200 deg) keep their color.
FISH_SKIN = band(75, 165, 0.25)
FISH_SCHEMES = [("base", None), ("deepsea", dict(shift=70)), ("reef", dict(shift=160)), ("sand", dict(shift=-75, sat=0.8))]
KOBOLD_SCHEMES = [("base", None), ("red", dict(shift=-50, sat=1.2)), ("slate", dict(shift=160, sat=0.8)),
                  ("ash", dict(sat=0.25, val=0.75))]


def races(jar):
    return [  # (team, base skin number, variant recipes)
        ("race_hobbit", 2, humanoid(2, hobbit_hair, HOBBIT_HAIR, hobbit_freckles)),
        ("race_elf", 3, humanoid(3, None, ELF_EYES, elf_circlet)),
        ("race_copper_legs", 4, copper(jar)),
        ("race_copper_wheel", 5, copper(jar)),
        ("race_fishfolk", 6, scales(FISH_SKIN, FISH_SCHEMES, fishfolk_pearls)),
        ("race_kobold", 7, scales(band(30, 80, 0.3), KOBOLD_SCHEMES, kobold_earrings)),
        ("race_dwarf", 8, humanoid(8, dwarf_hair, DWARF_HAIRS, dwarf_scar)),
    ]


def clear_copper_block(n):
    """Copper constructs hold nothing unless employed: clear the mini-block from the base skin."""
    for d in (TEX, RAND):
        p = f"{d}/villager{n}.png"
        im = Image.open(p).convert("RGBA")
        im.paste((0, 0, 0, 0), (45, 89, 77, 105))
        im.save(p)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))   # paths below are relative to the repo
    jar = zipfile.ZipFile(JAR)
    for n in (4, 5):
        clear_copper_block(n)
    rules, total = [], 0
    for team, n, recipes in races(jar):
        base = Image.open(f"{RAND}/villager{n}.png").convert("RGBA")
        for old in glob.glob(f"{RAND}/villager{n}[0-9][0-9].png"):   # drop variants from earlier runs
            os.remove(old)
        nums = [str(n)]
        k = 0
        for name, make in recipes:
            if name.startswith("base") and name.endswith(("base", "base/plain", "base/base/plain")):
                continue                                    # the untouched original keeps number n
            k += 1
            num = f"{n}{k:02d}"
            make(base.copy()).save(f"{RAND}/villager{num}.png")
            nums.append(num)
        if team in race_teams.COPPER_LOOKS:            # weathering stage is datapack state, not random
            rules += [(team + st, [num]) for st, num in zip(race_teams.COPPER_STAGES, nums)]
        else:
            rules.append((team, nums))
        total += len(nums)
        print(f"{team}: {len(nums)} looks")
    with open(f"{RAND}/villager.properties", "w", encoding="utf-8", newline="\n") as f:
        f.write(HDR + "".join(f"\nskins.{i}={' '.join(nums)}\nteams.{i}={team}\n" for i, (team, nums) in enumerate(rules, 1)))
    print(f"{total} base skins in total")


if __name__ == "__main__":
    main()

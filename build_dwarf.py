"""Build the dwarf race for the resource pack: model, base skin, vanilla-compatible overlays, rules.

Approach (same idea as the hobbit, but generated instead of hand-painted):
- 128x128 texture. The top-left 64x64 keeps the VANILLA villager layout, used by the parts that keep
  vanilla shape (head, nose, hat, hat rim, arms). Vanilla overlays line up there 1:1.
- The parts that change shape (shorter body, robe and legs) and the new beard get their own UV
  boxes in the right half. Every vanilla overlay is remapped onto them by dropping rows
  (widths/depths are unchanged, so no pixel is stretched).
- Legs hang off the body as submodels with their own hip pivot (the vanilla leg pivot is 6 px
  above a dwarf's hip). The body animation swings them with the vanilla walk formula.
- Overlays come straight from the vanilla textures in your Minecraft jar, so they stay vanilla.

Usage: python build_dwarf.py [path/to/26.3.jar]       (re-runnable; overwrites only dwarf files)
Writes: optifine/cem/villager8.jem, textures/entity/villager/villager8.png (+ random copy),
        optifine/random/entity/villager/{profession,type,profession_level}/<name>8.png,
        and adds a race_dwarf rule to every villager .properties file that lacks one.
"""
import io, json, os, random, sys, zipfile
from PIL import Image
from normalize_jem import normalize

NUM, TEAM = "8", "race_dwarf"
JAR = sys.argv[1] if len(sys.argv) > 1 else os.path.expandvars(r"%APPDATA%\.minecraft\versions\26.3\26.3.jar")
A = "server_resourcepack/assets/minecraft"
CEM, RAND, TEX = f"{A}/optifine/cem", f"{A}/optifine/random/entity/villager", f"{A}/textures/entity/villager"
HDR = "# Matches the villager's scoreboard team (set by the races datapack). No names needed.\n"

# ---- UV remapping ------------------------------------------------------------------------------
# name: (vanilla uv, dwarf uv, (w, h, d) of the dwarf box, vanilla rows kept on the side faces)
REMAP = {
    "body": ((16, 20), (64, 0), (8, 10, 6), [0, 1, 2, 3, 4, 5, 8, 9, 10, 11]),           # keeps collar + belt
    "robe": ((0, 38), (64, 16), (8, 14, 6), list(range(0, 7)) + list(range(13, 20))),     # keeps chest + hem
    "leg":  ((0, 22), (96, 0), (4, 6, 4), list(range(6, 12))),                            # keeps the feet
}
BEARD_UV = (96, 16)   # (8, 8, 1) box, base skin only


def remap(src64):
    """Vanilla 64x64 villager-layout texture -> 128x128 dwarf-layout texture."""
    out = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    out.paste(src64.crop((0, 0, 64, 64)), (0, 0))
    for (su, sv), (du, dv), (w, h, d), rows in REMAP.values():
        out.paste(src64.crop((su + d, sv, su + d + 2 * w, sv + d)), (du + d, dv))           # top + bottom
        for r, sr in enumerate(rows):                                                       # side strip
            out.paste(src64.crop((su, sv + d + sr, su + 2 * d + 2 * w, sv + d + sr + 1)), (du, dv + d + r))
    return out


# ---- base skin -------------------------------------------------------------------------------
HAIR = {"B": (122, 66, 32), "L": (138, 76, 37), "D": (104, 55, 26)}
GOLD, TROUSERS, TROUSERS_D = (222, 172, 52), (86, 72, 58), (72, 60, 48)
BOOT, BOOT_D, BOOT_L = (66, 44, 30), (50, 32, 20), (92, 62, 40)
rng = random.Random(8)


def hair():
    return HAIR[rng.choice("BBBBBBLLD")]    # low-contrast, vanilla-style shading


def paint_base(img):
    px = img.load()
    # ruddy, weathered skin; extra red on the nose
    for y in range(64):
        for x in range(64):
            r, g, b, a = px[x, y]
            if a and r > 140 and r > g > b and 50 < r - b < 110:
                k = (0.8, 0.78) if (24 <= x < 32 and y < 6) else (0.9, 0.85)
                px[x, y] = (r, int(g * k[0]), int(b * k[1]), a)
    fill = lambda x0, y0, x1, y1, f: [px.__setitem__((x, y), f()) for y in range(y0, y1) for x in range(x0, x1)]
    # head: top, back, under-chin
    fill(8, 0, 16, 8, hair); fill(24, 8, 32, 17, hair); fill(16, 0, 24, 8, hair)
    # right side (u runs back -> front, front edge x=7) and left side (front edge x=16)
    fill(0, 8, 8, 11, hair); fill(0, 11, 4, 17, hair); fill(6, 11, 8, 18, hair); fill(4, 15, 8, 18, hair)
    fill(16, 8, 24, 11, hair); fill(20, 11, 24, 17, hair); fill(16, 11, 18, 18, hair); fill(16, 15, 20, 18, hair)
    # face: hairline, temples, bushy split brows, sideburns down the face edges
    fill(8, 8, 16, 9, hair); fill(8, 9, 9, 18, hair); fill(15, 9, 16, 18, hair)
    for x in (9, 10, 13, 14):
        px[x, 12] = HAIR["D"]
    for x in (8, 9, 10, 13, 14, 15):
        px[x, 13] = HAIR["L"] if x in (9, 14) else HAIR["B"]
    px[11, 13] = px[12, 13] = px[11, 12]                                    # gap between the brows
    fill(9, 15, 15, 18, lambda: HAIR["B"])                                   # behind the beard
    # beard box (8,8,1): front pattern, '.' = transparent, G = gold braid ring
    beard = {"B": HAIR["B"], "L": (158, 92, 46), "D": (88, 45, 20)}   # crisper than the hair
    front = ["BLLBBLLB",
             "DBLBBLBD",
             "BBDDDDBB",
             "BLBBBBLB",
             "BBLBBLBB",
             ".BDBBDB.",
             ".BB..BB.",
             ".GG..GG."]
    col = lambda c: GOLD if c == "G" else beard[c]
    u, v = BEARD_UV
    for j, row in enumerate(front):
        for i, c in enumerate(row):
            if c != ".":
                px[u + 1 + i, v + 1 + j] = col(c)
        if row[0] != ".":
            px[u, v + 1 + j] = col(row[0])                                    # right side (+x edge)
        if row[7] != ".":
            px[u + 9, v + 1 + j] = col(row[7])                                # left side
    for i in range(8):
        px[u + 1 + i, v] = HAIR["B"]                                          # top
        if front[7][i] != ".":
            px[u + 9 + i, v] = col(front[7][i])                               # bottom
    # legs (4,6,4) at (96,0): trousers then boots, soles underneath
    lu, lv = REMAP["leg"][1]
    for x in range(lu + 4, lu + 8):
        for y in range(lv, lv + 4):
            px[x, y] = TROUSERS                                               # top
    for x in range(lu + 8, lu + 12):
        for y in range(lv, lv + 4):
            px[x, y] = BOOT_D                                                 # sole
    for r in range(6):
        for x in range(lu, lu + 16):
            if r < 3:
                px[x, lv + 4 + r] = TROUSERS_D if r == 2 or rng.random() < 0.25 else TROUSERS
            else:
                px[x, lv + 4 + r] = BOOT_L if r == 3 else (BOOT_D if r == 5 else BOOT)
    return img


# ---- model -----------------------------------------------------------------------------------
# Authored with natural dwarf pivots (head on the neck at y=16); normalize_jem.py then moves the
# named parts to the vanilla pivots EMF uses, compensating rotated parts, without moving geometry.
TS = [128, 128]
LEG_SWING = "cos(limb_swing * 0.6662) * 0.7 * limb_speed"            # vanilla villager walk
MODEL = {"credit": "Generated by build_dwarf.py", "textureSize": TS, "models": [
    {"part": "head", "id": "head", "invertAxis": "xy", "translate": [0, -16, 0], "textureSize": TS, "boxes": [
        {"coordinates": [-4, 16, -4, 8, 10, 8], "textureOffset": [0, 0]},
        {"coordinates": [-4, 11, -5, 8, 8, 1], "textureOffset": list(BEARD_UV)}]},
    {"part": "nose", "id": "nose", "invertAxis": "xy", "translate": [0, -18, 0], "textureSize": TS, "boxes": [
        {"coordinates": [-1, 15, -6, 2, 4, 2], "textureOffset": [24, 0]}]},
    {"part": "headwear", "id": "headwear", "invertAxis": "xy", "translate": [0, -16, 0], "textureSize": TS, "boxes": [
        {"coordinates": [-4, 16, -4, 8, 10, 8], "textureOffset": [32, 0], "sizeAdd": 0.51}]},
    {"part": "headwear2", "id": "headwear2", "invertAxis": "xy", "translate": [0, -16, 0], "rotate": [90, 0, 0],
     "textureSize": TS, "boxes": [{"coordinates": [-8, 8, -6, 16, 16, 1], "textureOffset": [30, 47]}],
     "animations": [{"this.rx": 0}]},
    {"part": "body", "id": "body", "invertAxis": "xy", "translate": [0, -16, 0], "textureSize": TS, "boxes": [
        {"coordinates": [-4, 6, -3, 8, 10, 6], "textureOffset": list(REMAP["body"][1])}],
     "submodels": [
        {"id": "dwarf_leg_r", "invertAxis": "xy", "translate": [2, 6, 0], "boxes": [
            {"coordinates": [-2, -6, -2, 4, 6, 4], "textureOffset": list(REMAP["leg"][1])}]},
        {"id": "dwarf_leg_l", "invertAxis": "xy", "translate": [-2, 6, 0], "boxes": [
            {"coordinates": [-2, -6, -2, 4, 6, 4], "textureOffset": list(REMAP["leg"][1])}]}],
     "animations": [{"dwarf_leg_r.rx": LEG_SWING, "dwarf_leg_l.rx": "-" + LEG_SWING}]},
    {"part": "bodywear", "id": "bodywear", "invertAxis": "xy", "translate": [0, -16, 0], "textureSize": TS, "boxes": [
        {"coordinates": [-4, 2, -3, 8, 14, 6], "textureOffset": list(REMAP["robe"][1]), "sizeAdd": 0.5}]},
    {"part": "arms", "id": "arms", "invertAxis": "xy", "translate": [0, -14.05, 1.05], "rotate": [43, 0, 0],
     "textureSize": TS, "boxes": [
        {"coordinates": [-4, 8.05, -3.05, 8, 4, 4], "textureOffset": [40, 38]},
        {"coordinates": [4, 8.05, -3.05, 4, 8, 4], "textureOffset": [44, 22]}],
     "submodels": [{"id": "mirrored", "invertAxis": "xy", "mirrorTexture": "u", "translate": [0, 0, 0], "boxes": [
        {"coordinates": [-8, 8.05, -3.05, 4, 8, 4], "textureOffset": [44, 22]}]}],
     "animations": [{"this.rx": 0}]},
    # vanilla legs are hidden; the visible legs are the body submodels above
    {"part": "right_leg", "id": "right_leg", "invertAxis": "xy", "translate": [-2, -12, 0], "textureSize": TS},
    {"part": "left_leg", "id": "left_leg", "invertAxis": "xy", "translate": [2, -12, 0], "textureSize": TS},
]}


# ---- properties rules ------------------------------------------------------------------------
def add_rule(path, key, value):
    text = open(path, encoding="utf-8").read() if os.path.exists(path) else HDR
    if f"={TEAM}" in text:
        return
    nums = [int(line.split("=")[0].split(".")[1]) for line in text.splitlines()
            if line.startswith(("skins.", "models.")) and "=" in line]
    n = max(nums, default=0) + 1
    weights = f"weights.{n}=100\n" if "weights." in text else ""
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{'' if text.endswith(chr(10) * 2) else chr(10)}{key}.{n}={value}\n{weights}teams.{n}={TEAM}\n")


def main():
    jar = zipfile.ZipFile(JAR)
    vanilla = lambda rel: Image.open(io.BytesIO(jar.read(f"assets/minecraft/textures/entity/villager/{rel}"))).convert("RGBA")

    base = paint_base(remap(vanilla("villager.png")))
    for d in (TEX, RAND):
        base.save(f"{d}/villager{NUM}.png")

    count = 0
    for sub in ("profession", "type", "profession_level"):
        names = sorted(n.rsplit("/", 1)[1][:-4] for n in jar.namelist()
                       if n.startswith(f"assets/minecraft/textures/entity/villager/{sub}/") and n.endswith(".png"))
        for name in names:
            remap(vanilla(f"{sub}/{name}.png")).save(f"{RAND}/{sub}/{name}{NUM}.png")
            add_rule(f"{RAND}/{sub}/{name}.properties", "skins", NUM)
            count += 1
    add_rule(f"{RAND}/villager.properties", "skins", NUM)
    add_rule(f"{CEM}/villager.properties", "models", NUM)

    jem = f"{CEM}/villager{NUM}.jem"
    with open(jem, "w", encoding="utf-8", newline="\n") as f:
        json.dump(MODEL, f, indent="\t")
    normalize(jem)
    print(f"dwarf: model, base skin and {count} overlays written")


if __name__ == "__main__":
    main()

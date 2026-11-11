"""Custom profession overlays for copper constructs, fishfolk and kobolds (no biome/level overlays).

- Copper construct (legs + wheel share one UV layout): the 8x8x8 mini-block carries a product of
  the job, built from the vanilla block/item textures in your jar, and the flat 16x8 item plane
  carries a hand-drawn tool. Unemployed constructs hold nothing (base skin is empty there).
- Fishfolk: sea-themed takes on each job (kelp, shell, coral, pearl, prismarine, nets).
- Kobold: underground takes (scrap iron, bone, leather, mushroom caps, candle and miner gear).

Biome and level overlays for these races are transparent, so only the profession shows.
Usage: python build_race_professions.py [path/to/26.3.jar]       (re-runnable)
To change a design, edit its function below and re-run; preview with preview_jem.py.
"""
import io, os, random, sys, zipfile
from PIL import Image
import glob
import race_teams

JAR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.expandvars(r"%APPDATA%\.minecraft\versions\26.3\26.3.jar")
RAND = "server_resourcepack/assets/minecraft/optifine/random/entity/villager"
HDR = "# Matches the villager's scoreboard team (set by the races datapack). No names needed.\n"
PROFESSIONS = ["armorer", "butcher", "cartographer", "cleric", "farmer", "fisherman", "fletcher",
               "leatherworker", "librarian", "mason", "nitwit", "shepherd", "toolsmith", "weaponsmith"]


# ---- box-UV canvas -------------------------------------------------------------------------
class Canvas:
    """Paint on Minecraft box-UV faces. A box is (u, v, w, h, d). On the side strip, columns run
    right side (back->front), front (entity's right->left), left side (front->back), back."""

    def __init__(self, size, seed):
        self.img = Image.new("RGBA", size, (0, 0, 0, 0))
        self.px = self.img.load()
        self.rng = random.Random(seed)

    def set(self, x, y, c):
        if c:
            self.px[x, y] = tuple(max(0, min(255, int(v))) for v in c[:3]) + (255,)

    def jitter(self, c, amt=10):
        d = self.rng.randint(-amt, amt)
        return tuple(v + d for v in c)

    def face(self, box, name, fn):
        u, v, w, h, d = box
        x0, y0, fw, fh = {"top": (u + d, v, w, d), "bottom": (u + d + w, v, w, d), "right": (u, v + d, d, h),
                          "front": (u + d, v + d, w, h), "left": (u + d + w, v + d, d, h),
                          "back": (u + 2 * d + w, v + d, w, h)}[name]
        for j in range(fh):
            for i in range(fw):
                self.set(x0 + i, y0 + j, fn(i, j, fw, fh))

    def rows(self, box, rows, fn):
        """fn(col, row, side, i_in_face) over the whole side strip for the given rows."""
        u, v, w, h, d = box
        spans = [("right", d), ("front", w), ("left", d), ("back", w)]
        for r in rows:
            col = 0
            for side, n in spans:
                for i in range(n):
                    self.set(u + col, v + d + r, fn(col, r, side, i))
                    col += 1

    def sprite(self, box, name, art, pal, mirror=False):
        def fn(i, j, fw, fh):
            if j >= len(art):
                return None
            line = art[j][::-1] if mirror else art[j]
            return pal.get(line[i]) if i < len(line) else None
        self.face(box, name, fn)


def solid(c, cv, amt=8):
    return lambda *a: cv.jitter(c, amt)


# ---- copper construct ----------------------------------------------------------------------
MINI = (45, 89, 8, 8, 8)          # body submodel "handheld"
ITEM = (17, 44, 1, 8, 16)         # arms submodel "handheld2": 16x8 faces on its left/right sides

# (product: ("block", top, side) | ("item", name) | None, tool sprite)
COPPER = {
    "armorer": (("block", "iron_block", "iron_block"), "hammer"),
    "butcher": (("item", "beef"), "cleaver"),
    "cartographer": (("item", "map"), "spyglass"),
    "cleric": (("block", "glowstone", "glowstone"), "potion"),
    "farmer": (("block", "hay_block_top", "hay_block_side"), "hoe"),
    "fisherman": (("block", "barrel_top", "barrel_side"), "rod"),
    "fletcher": (("block", "target_top", "target_side"), "arrow"),
    "leatherworker": (("item", "leather"), "knife"),
    "librarian": (("block", "oak_planks", "bookshelf"), "book"),
    "mason": (("block", "stone_bricks", "stone_bricks"), "pickaxe"),
    "nitwit": (("block", "coarse_dirt", "coarse_dirt"), "stick"),
    "shepherd": (("block", "white_wool", "white_wool"), "shears"),
    "toolsmith": (("block", "raw_iron_block", "raw_iron_block"), "axe"),
    "weaponsmith": (("block", "gold_block", "gold_block"), "sword"),
}
TOOL_PAL = {"W": (104, 78, 46), "w": (140, 104, 62), "I": (222, 222, 222), "i": (150, 150, 150), "d": (80, 80, 80),
            "C": (206, 112, 72), "c": (140, 70, 42), "g": (180, 226, 236), "k": (150, 108, 66), "P": (176, 72, 206),
            "p": (240, 232, 210), "L": (120, 108, 98), "b": (112, 62, 32), "F": (236, 236, 236), "f": (176, 176, 176),
            "S": (226, 226, 226), "R": (176, 46, 40), "Y": (232, 196, 48), "y": (196, 150, 30), "G": (88, 66, 40)}
# handle on the left (back of the plane), working end on the right (front, pointing forward)
TOOLS = {
    "hammer":   ["............iii.", "...........iIIIi", "...........iIIIi", "wwwwwwwwwwwiIIIi",
                 "WWWWWWWWWWWiIIIi", "...........iIIIi", "............iii."],
    "cleaver":  ["", "........iiiiiiii", "........iIIIIIIi", "wwwwwwwwiIIIIIIi", "WWWWWWWWiIIIIIIi",
                 "........iIIIIIIi", "........iiiiiiii"],
    "spyglass": ["", "", "...cccccccccccc.", "..cCCCCCCCCCCCCg", "..cCCCCCCCCCCCCg", "...cccccccccccc."],
    "potion":   ["", "..........gggg..", "...gg....gPPPPg.", "..kkgggggPPPPPPg", "..kkgggggPPPPPPg",
                 "...gg....gPPPPg.", "..........gggg.."],
    "hoe":      ["", "............IIII", "............IIii", "wwwwwwwwwwwwww..", "WWWWWWWWWWWWWW.."],
    "rod":      ["..............WW", "..........wwWW.S", "......wwWW.....S", "..wwWW.........S",
                 "WW.............S", "...............S", "..............ii", "...............i"],
    "arrow":    ["", "", "F.F...........i.", ".fFwwwwwwwwwwwdd", "F.F...........i."],
    "knife":    ["", "", "..........IIIII.", "wwwwwwwwiIIIIIIi", "WWWWWWWWi.......", ""],
    "book":     [".pppppp..pppppp.", "bpLLLLpbbpLLLLpb", "bppppppbbppppppb", "bpLLLppbbpLLLLpb",
                 "bppppppbbppppppb", "bpLLLLpbbpLLLppb", "bppppppbbppppppb", ".bbbbbbbbbbbbbb."],
    "pickaxe":  ["...........iii..", ".............Ii.", "wwwwwwwwwwwwwwIi", "WWWWWWWWWWWWWWIi",
                 ".............Ii.", "...........iii.."],
    "stick":    ["", "", "..........w.....", "wwwwwwwwwwWwwwww", "WWWWWWWWWWWWWWW.", ""],
    "shears":   ["", ".RR......IIIIII.", "R.R.....IIIIII..", ".RRiiiiii.......", "R.R.....iiiiii..",
                 ".RR......iiiiii."],
    "axe":      ["...........IIII.", "...........IIIII", "wwwwwwwwwwwwIIII", "WWWWWWWWWWWWIII.", "...........ii..."],
    "sword":    ["", "....d...........", "....dIIIIIIIIIi.", "wwWWdIIIIIIIIIIi", "....diiiiiiiiii.", "....d..........."],
}


def copper_overlay(prof, jar):
    cv = Canvas((128, 128), prof)
    product, tool = COPPER[prof]
    if product:
        if product[0] == "block":
            load = lambda n: Image.open(io.BytesIO(jar.read(f"assets/minecraft/textures/block/{n}.png"))).convert("RGBA")
            top, side = load(product[1]), load(product[2])
        else:   # an item: use its middle 8x8 (mostly the item's material) on every face
            it = Image.open(io.BytesIO(jar.read(f"assets/minecraft/textures/item/{product[1]}.png"))).convert("RGBA")
            top = side = it.crop((4, 4, 12, 12)).resize((16, 16), Image.NEAREST)
        small = {k: im.crop((0, 0, 16, 16)).resize((8, 8), Image.BOX).load() for k, im in (("top", top), ("side", side))}
        for name in ("top", "bottom", "right", "front", "left", "back"):
            src = small["top" if name in ("top", "bottom") else "side"]
            cv.face(MINI, name, lambda i, j, fw, fh, s=src: s[i, j] if s[i, j][3] > 60 else None)
    cv.sprite(ITEM, "right", TOOLS[tool], TOOL_PAL)   # outer face only; the inner face stays transparent
    return cv.img


# ---- fishfolk ------------------------------------------------------------------------------
F = dict(HW=(96, 88, 8, 7, 8), BODY=(67, 82, 8, 12, 6), KILT=(100, 63, 8, 6, 6))
KELP, KELP_D = (70, 120, 44), (44, 84, 30)
SHELL, SHELL_D = (234, 224, 200), (196, 178, 146)
CORAL, CORAL_D = (232, 96, 112), (176, 58, 80)
PEARL = (244, 242, 236)
PRISM, PRISM_D, PRISM_L = (92, 160, 150), (52, 104, 98), (150, 210, 196)
NET = (186, 160, 112)
PURPLE, PURPLE_D = (132, 70, 170), (92, 44, 126)
EYE_ROWS = (3, 4, 5)          # rows of the fishfolk hat layer's front face that cover the eyes


def f_cap(cv, color, shade, rows=2):
    cv.face(F["HW"], "top", solid(color, cv))
    cv.rows(F["HW"], range(rows), lambda c, r, s, i: cv.jitter(shade if r == rows - 1 else color))


def f_band(cv, row, colors):
    cv.rows(F["HW"], [row], lambda c, r, s, i: colors[c % len(colors)])


def f_torso(cv, rows, fn):
    cv.rows(F["BODY"], rows, fn)


def fishfolk_overlay(prof):
    cv = Canvas((128, 128), "fish" + prof)
    B = F["BODY"]
    if prof == "armorer":        # prismarine breastplate + shell helmet
        f_torso(cv, range(0, 8), lambda c, r, s, i: PRISM_L if (r in (0, 7) or (c + r) % 5 == 0) else cv.jitter(PRISM if (c // 2 + r // 2) % 2 else PRISM_D, 5))
        f_cap(cv, SHELL, SHELL_D, 3)
        f_band(cv, 1, [SHELL_D, SHELL])
        cv.rows(F["KILT"], range(0, 3), lambda c, r, s, i: PRISM_L if r == 0 else cv.jitter(PRISM if c % 3 else PRISM_D, 5))
    elif prof == "butcher":      # stained shell-leather apron + coral headband
        cv.face(B, "front", lambda i, j, fw, fh: None if j < 2 else (CORAL_D if cv.rng.random() < 0.12 else cv.jitter(SHELL, 6)))
        f_torso(cv, [2], lambda c, r, s, i: SHELL_D)
        f_band(cv, 2, [CORAL, CORAL_D])
        cv.face(F["KILT"], "front", lambda i, j, fw, fh: CORAL_D if cv.rng.random() < 0.12 else cv.jitter(SHELL, 6))
    elif prof == "cartographer":  # rolled-chart sash + sea-glass monocle
        cv.face(B, "front", lambda i, j, fw, fh: NET if abs(i - (fw - 1 - j * fw // fh)) <= 1 else None)
        cv.face(B, "back", lambda i, j, fw, fh: NET if abs(i - j * fw // fh) <= 1 else None)
        cv.face(F["HW"], "front", lambda i, j, fw, fh: (120, 206, 206) if (j in (3, 5) and i in (5, 6, 7)) or (j == 4 and i in (5, 7)) else None)
    elif prof == "cleric":       # purple coral crown + pearl-studded stole
        f_band(cv, 0, [PURPLE, CORAL, PURPLE, None])
        f_band(cv, 1, [PURPLE_D])
        cv.face(B, "front", lambda i, j, fw, fh: (PEARL if j % 3 == 1 else PURPLE) if i in (1, 2, 5, 6) else None)
        cv.face(B, "back", lambda i, j, fw, fh: PURPLE if 2 <= i <= 5 else None)
        f_torso(cv, [0], lambda c, r, s, i: PURPLE_D)
    elif prof == "farmer":       # kelp wreath + kelp fringe skirt
        f_band(cv, 1, [KELP, KELP_D, (120, 170, 60)])
        f_band(cv, 0, [None, KELP, None, None, KELP_D])
        f_torso(cv, range(8, 12), lambda c, r, s, i: (KELP if c % 2 else KELP_D) if r - 8 < (2 + (c * 7) % 3) else None)
        f_torso(cv, [8], lambda c, r, s, i: (90, 70, 40))
        cv.rows(F["KILT"], range(0, 6), lambda c, r, s, i: (KELP if c % 2 else KELP_D) if r < 3 + (c * 7) % 4 else None)
    elif prof == "fisherman":    # knotted net shawl with a bobber + net cap
        f_torso(cv, range(0, 5), lambda c, r, s, i: NET if (c + r) % 2 == 0 or r == 0 else None)
        cv.face(B, "front", lambda i, j, fw, fh: {(2, 3): (220, 50, 40), (2, 4): (240, 240, 240)}.get((i, j)))
        cv.face(F["HW"], "top", lambda i, j, fw, fh: NET if (i + j) % 2 == 0 else None)
        f_band(cv, 0, [NET, None])
    elif prof == "fletcher":     # spine quiver on the back, fin plume on the head
        cv.face(B, "front", lambda i, j, fw, fh: (110, 80, 50) if abs(i - (fw - 1 - j * fw // fh)) == 0 else None)
        cv.face(B, "back", lambda i, j, fw, fh: ((236, 236, 236) if j == 0 else (120, 86, 52)) if i in (3, 4) and j < 9 else None)
        cv.face(F["HW"], "top", lambda i, j, fw, fh: ((240, 240, 240) if j % 2 else (200, 70, 60)) if i in (3, 4) else None)
        f_band(cv, 0, [None, None, None, None, None, None, None, None, None, None, (200, 70, 60), None, None])
    elif prof == "leatherworker":  # turtle-shell vest, open at the front
        scute = lambda c, r: cv.jitter((74, 140, 62) if (c // 3 + r // 3) % 2 else (54, 110, 46), 5)
        cv.face(B, "back", lambda i, j, fw, fh: scute(i, j) if j < 9 else None)
        for side in ("left", "right"):
            cv.face(B, side, lambda i, j, fw, fh: scute(i, j) if j < 9 else None)
        cv.face(B, "front", lambda i, j, fw, fh: scute(i, j) if j < 9 and i in (0, 1, 6, 7) else None)
    elif prof == "librarian":    # book hat + shell spectacles
        cv.face(F["HW"], "top", solid((110, 50, 34), cv, 5))
        cv.rows(F["HW"], [0], lambda c, r, s, i: (110, 50, 34))
        cv.rows(F["HW"], [1], lambda c, r, s, i: (240, 232, 210) if s != "back" else (110, 50, 34))
        rims = {(i, j) for i in (0, 1, 2, 5, 6, 7) for j in (3, 5)} | {(0, 4), (2, 4), (5, 4), (7, 4), (3, 4), (4, 4)}
        cv.face(F["HW"], "front", lambda i, j, fw, fh: SHELL_D if (i, j) in rims else None)
    elif prof == "mason":        # prismarine-brick apron + sponge headband
        cv.face(B, "front", lambda i, j, fw, fh: None if j < 3 else (PRISM_D if j % 3 == 0 or (i + (j // 3) * 2) % 4 == 0 else cv.jitter(PRISM, 6)))
        f_band(cv, 2, [(216, 196, 74), (190, 170, 50)])
        cv.face(F["KILT"], "front", lambda i, j, fw, fh: PRISM_D if j % 3 == 0 or (i + (j // 3) * 2) % 4 == 0 else cv.jitter(PRISM, 6))
    elif prof == "nitwit":       # tangled seaweed on the head
        cv.face(F["HW"], "top", lambda i, j, fw, fh: cv.jitter(KELP) if cv.rng.random() < 0.55 else None)
        cv.rows(F["HW"], range(0, 5), lambda c, r, s, i: (KELP if c % 3 else KELP_D) if r < (c * 5) % 4 + 1 else None)
    elif prof == "shepherd":     # fluffy wool shawl
        f_torso(cv, range(0, 4), lambda c, r, s, i: cv.jitter((236, 234, 228), 10) if r < 3 or c % 2 else None)
    elif prof == "toolsmith":    # leather belt with pearl studs + orange coral headband
        f_torso(cv, [8, 9], lambda c, r, s, i: PEARL if r == 8 and c % 3 == 1 else (86, 58, 34))
        cv.face(B, "front", lambda i, j, fw, fh: (150, 150, 150) if i == 6 and 10 <= j <= 11 else None)
        f_band(cv, 2, [(236, 132, 60), (200, 96, 40)])
        cv.rows(F["KILT"], [0], lambda c, r, s, i: PEARL if c % 3 == 1 else (86, 58, 34))
        cv.face(F["KILT"], "front", lambda i, j, fw, fh: (170, 170, 176) if i == 6 and 1 <= j <= 3 else ((110, 80, 50) if i == 6 and j == 4 else None))
    elif prof == "weaponsmith":  # shark-tooth necklace + coral eyepatch
        cv.face(B, "front", lambda i, j, fw, fh: ((236, 232, 220) if (j == 0 or (j == 1 and i % 2 == 0)) else None))
        f_torso(cv, [0], lambda c, r, s, i: (90, 64, 40) if s != "front" else None)
        f_band(cv, 4, [(60, 40, 30)])
        cv.face(F["HW"], "front", lambda i, j, fw, fh: CORAL_D if j in (3, 4, 5) and 5 <= i <= 7 else ((60, 40, 30) if j == 4 else None))
    return cv.img


# ---- kobold --------------------------------------------------------------------------------
K = dict(HW=(35, 2, 6, 8, 6), BW=(1, 38, 6, 14, 6))
IRON, IRON_D, RUST = (156, 156, 160), (96, 96, 102), (140, 84, 48)
HIDE, HIDE_D, HIDE_L = (118, 82, 48), (80, 54, 30), (156, 116, 72)
BONE, BONE_D = (230, 222, 196), (186, 176, 146)


def k_cap(cv, color, shade, rows):
    cv.face(K["HW"], "top", lambda *a: cv.jitter(color))
    cv.rows(K["HW"], range(rows), lambda c, r, s, i: cv.jitter(shade if r == rows - 1 else color))


def k_strip(cv, rows, fn):
    cv.rows(K["BW"], rows, fn)


def kobold_overlay(prof):
    cv = Canvas((64, 64), "kob" + prof)
    BW, HW = K["BW"], K["HW"]
    diag = lambda i, j, fw, fh, flip=False: abs((fw - 1 - i if flip else i) - j * fw // 10) == 0 and j < 10
    if prof == "armorer":        # riveted scrap helmet + chain shirt
        k_cap(cv, IRON, IRON_D, 4)
        cv.rows(HW, [1], lambda c, r, s, i: RUST if c % 4 == 0 else IRON)
        k_strip(cv, range(0, 8), lambda c, r, s, i: IRON if (c + r) % 2 else IRON_D)
    elif prof == "butcher":      # stained leather apron
        cv.face(BW, "front", lambda i, j, fw, fh: None if j < 2 else ((150, 40, 36) if cv.rng.random() < 0.15 else cv.jitter(HIDE, 6)))
        k_strip(cv, [2], lambda c, r, s, i: HIDE_D)
    elif prof == "cartographer":  # brass goggles strapped round the head + map satchel strap
        cv.rows(HW, [4], lambda c, r, s, i: (200, 160, 60) if s in ("left", "right") and i in (1, 2) else HIDE_D)
        cv.face(BW, "front", lambda i, j, fw, fh: (214, 190, 130) if diag(i, j, fw, fh) else None)
        cv.face(BW, "left", lambda i, j, fw, fh: (170, 130, 80) if 6 <= j <= 9 and 1 <= i <= 4 else None)
    elif prof == "cleric":       # purple hood + bone charm necklace
        cv.face(HW, "top", lambda *a: cv.jitter((110, 58, 150)))
        cv.rows(HW, range(0, 7), lambda c, r, s, i: None if (s == "front" and r >= 2) else cv.jitter((110, 58, 150) if r < 6 else (80, 40, 110)))
        k_strip(cv, [1], lambda c, r, s, i: BONE if c % 2 == 0 else BONE_D if s == "front" else None)
    elif prof == "farmer":       # red mushroom cap + belt pouch
        cv.face(HW, "top", lambda i, j, fw, fh: (240, 236, 226) if (i, j) in ((1, 1), (4, 2), (2, 4), (4, 4)) else cv.jitter((190, 40, 36), 6))
        cv.rows(HW, [0, 1, 2], lambda c, r, s, i: (240, 236, 226) if r == 0 and c % 5 == 2 else cv.jitter((170, 32, 30), 6))
        cv.rows(HW, [3], lambda c, r, s, i: (226, 214, 186))
        k_strip(cv, [8], lambda c, r, s, i: HIDE_D)
        cv.face(BW, "front", lambda i, j, fw, fh: HIDE_L if 9 <= j <= 10 and 3 <= i <= 4 else None)
    elif prof == "fisherman":    # felt bucket hat + net bag on the back
        k_cap(cv, (110, 92, 60), (84, 70, 44), 4)
        cv.face(BW, "back", lambda i, j, fw, fh: (196, 170, 120) if 3 <= j <= 9 and (i + j) % 2 == 0 else None)
        k_strip(cv, [1], lambda c, r, s, i: (196, 170, 120) if s in ("left", "right") and i == 2 else None)
    elif prof == "fletcher":     # feather crest + quiver on the back
        cv.rows(HW, [0, 1], lambda c, r, s, i: [(200, 50, 40), (240, 240, 240), (40, 40, 40)][c % 3] if (s in ("back", "left", "right") and (r == 0 or c % 2)) else None)
        cv.face(BW, "front", lambda i, j, fw, fh: HIDE_D if diag(i, j, fw, fh) else None)
        cv.face(BW, "back", lambda i, j, fw, fh: ((240, 240, 240) if j == 0 else HIDE) if 2 <= i <= 3 and j < 9 else None)
    elif prof == "leatherworker":  # patchwork hide vest
        k_strip(cv, range(0, 10), lambda c, r, s, i: None if (s == "front" and 2 <= i <= 3) else cv.jitter([HIDE, HIDE_D, HIDE_L][(c // 3 + r // 3) % 3], 5))
    elif prof == "librarian":    # wax candle helmet + scholar's sash
        k_cap(cv, (226, 206, 140), (180, 150, 70), 4)
        cv.face(HW, "front", lambda i, j, fw, fh: {(2, 0): (255, 196, 60), (3, 0): (255, 150, 40), (2, 1): (240, 230, 190), (3, 1): (240, 230, 190)}.get((i, j)))
        cv.face(BW, "front", lambda i, j, fw, fh: (120, 50, 150) if diag(i, j, fw, fh, True) else None)
        cv.face(BW, "back", lambda i, j, fw, fh: (120, 50, 150) if diag(i, j, fw, fh) else None)
    elif prof == "mason":        # miner's hard hat with a lamp + stone-dust apron
        k_cap(cv, (220, 184, 40), (170, 136, 24), 4)
        cv.face(HW, "front", lambda i, j, fw, fh: (255, 230, 120) if j == 1 and i in (2, 3) else None)
        cv.face(BW, "front", lambda i, j, fw, fh: None if j < 4 else cv.jitter((150, 150, 146), 8))
    elif prof == "nitwit":       # a cooking pot worn as a hat
        k_cap(cv, (64, 64, 70), (40, 40, 44), 4)
        cv.rows(HW, [3], lambda c, r, s, i: (100, 100, 108))
        cv.face(HW, "top", lambda i, j, fw, fh: (30, 30, 34) if 1 <= i <= 4 and 1 <= j <= 4 else (64, 64, 70))
    elif prof == "shepherd":     # fluffy wool collar + tuft
        k_strip(cv, range(0, 3), lambda c, r, s, i: cv.jitter((238, 236, 230), 10) if r < 2 or c % 2 else None)
    elif prof == "toolsmith":    # tool belt + dark goggles band
        k_strip(cv, [8, 9], lambda c, r, s, i: (170, 170, 176) if r == 8 and c % 4 == 1 else HIDE_D)
        cv.rows(HW, [3], lambda c, r, s, i: (30, 30, 34) if s in ("left", "right") and i in (1, 2) else HIDE_D)
    elif prof == "weaponsmith":  # skull helm + red war sash
        k_cap(cv, BONE, BONE_D, 4)
        cv.face(HW, "front", lambda i, j, fw, fh: (40, 30, 26) if j == 2 and i in (1, 4) else None)
        cv.face(BW, "front", lambda i, j, fw, fh: (160, 30, 30) if diag(i, j, fw, fh) else None)
        cv.face(BW, "back", lambda i, j, fw, fh: (160, 30, 30) if diag(i, j, fw, fh, True) else None)
    return cv.img


# ---- rules ---------------------------------------------------------------------------------
def add_rule(path, num, team):
    text = open(path, encoding="utf-8").read() if os.path.exists(path) else HDR
    if any(l.startswith("teams.") and team in l.split("=", 1)[1].split() for l in text.splitlines()):
        return
    nums = [int(l.split("=")[0].split(".")[1]) for l in text.splitlines() if l.startswith("skins.") and "=" in l]
    n = max(nums, default=0) + 1
    weights = f"weights.{n}=100\n" if "weights." in text else ""
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{'' if text.endswith(chr(10) * 2) else chr(10)}skins.{n}={num}\n{weights}teams.{n}={team}\n")


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))   # paths below are relative to the repo
    jar = zipfile.ZipFile(JAR)
    for prof in PROFESSIONS:
        img = copper_overlay(prof, jar)
        img.save(f"{RAND}/profession/{prof}4.png")
        img.save(f"{RAND}/profession/{prof}5.png")
        fishfolk_overlay(prof).save(f"{RAND}/profession/{prof}6.png")
        kobold_overlay(prof).save(f"{RAND}/profession/{prof}7.png")
        add_rule(f"{RAND}/profession/{prof}.properties", 4, "race_copper_legs")
    # copper legs used to hide overlays with per-part texture pins; give it transparent biome/level overlays
    for sub in ("type", "profession_level"):
        for fn in os.listdir(f"{RAND}/{sub}"):
            if fn.endswith(".properties"):
                name = fn[:-len(".properties")]
                Image.new("RGBA", (128, 128), (0, 0, 0, 0)).save(f"{RAND}/{sub}/{name}4.png")
                add_rule(f"{RAND}/{sub}/{fn}", 4, "race_copper_legs")
    # copper constructs change team as they weather: every overlay/model rule must list all stage teams
    files = glob.glob(f"{RAND}/*/*.properties") + ["server_resourcepack/assets/minecraft/optifine/cem/villager.properties"]
    n = sum(race_teams.expand_copper(f) for f in files)
    print(f"{len(PROFESSIONS)} professions x copper/fishfolk/kobold written; copper stage teams added to {n} rule files")


if __name__ == "__main__":
    main()

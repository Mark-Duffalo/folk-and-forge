"""Generate the race contract item textures, models and item definitions in the resource pack.

Each contract is a parchment scroll with a wax seal in the race's colours and a 3x3 emblem.
Edit PALETTES / EMBLEMS and re-run:  python build_contract_textures.py
Writes under server_resourcepack/assets/races/ (items/, models/item/, textures/item/contract/).
The datapack points each contract at its model with item_model="races:contract/<race>".
"""
import json, os
from PIL import Image

RP = "server_resourcepack/assets/races"

# Scroll, 16x16. O outline, R roll, r roll highlight, P parchment, p parchment shade, L ink line.
SCROLL = [
    "................",
    ".OOOOOOOOOOOOOO.",
    "ORrrrrrrrrrrrrRO",
    "ORRRRRRRRRRRRRRO",
    ".OOPPPPPPPPPPOO.",
    "..OPPPPPPPPPpO..",
    "..OPLLLLLLLPpO..",
    "..OPPPPPPPPPpO..",
    "..OPLLLLLLPPpO..",
    "..OPPPPPPPPPpO..",
    "..OPLLLLPPPPpO..",
    "..OPPPPPPPPPpO..",
    ".OOPPPPPPPPPPOO.",
    "ORrrrrrrrrrrrrRO",
    "ORRRRRRRRRRRRRRO",
    ".OOOOOOOOOOOOOO.",
]
SCROLL_COLORS = {"O": "#5a3b1e", "R": "#c9a66b", "r": "#e8cf98",
                 "P": "#f3e3b5", "p": "#e2c98f", "L": "#9c7a52"}

# Wax seal, 7x7, top-left at (x=8, y=8). D dark rim, S wax, H shine, e = emblem slot.
SEAL = [
    "..DDD..",
    ".DSHSD.",
    "DSeeeSD",
    "DSeeeSD",
    "DSeeeSD",
    ".DSSSD.",
    "..DDD..",
]
SEAL_AT = (8, 8)
RIBBON = [(9, 14), (8, 15), (13, 14), (14, 15)]   # two ribbon tails under the seal

# 3x3 emblems, E = emblem colour, anything else = wax.
EMBLEMS = {
    "hobbit":   [".EE", "EEE", "E.."],   # leaf on a stem
    "elf":      [".E.", "EEE", ".E."],   # star
    "copper":   ["EEE", "E.E", "EEE"],   # cog ring
    "fishfolk": [".E.", "EEE", "EEE"],   # water drop
    "kobold":   ["E.E", "EEE", ".E."],   # horned head
    "dwarf":    ["EEE", ".E.", ".E."],   # hammer
}
#             dark rim   wax        shine      emblem
PALETTES = {
    "hobbit":   ("#2f5a1e", "#4f8a2c", "#7cb84a", "#e8c547"),   # green wax, gold leaf
    "elf":      ("#26305e", "#3d4f9a", "#6f86d6", "#e8eefc"),   # blue wax, silver star
    "copper":   ("#7a3a1a", "#c06a35", "#e8975a", "#4fa38a"),   # copper wax, verdigris cog
    "fishfolk": ("#12525e", "#1f8a99", "#4fc4cf", "#e6fbff"),   # teal wax, white drop
    "kobold":   ("#5e1414", "#9a2a22", "#cf5244", "#efe2c2"),   # red wax, bone horns
    "dwarf":    ("#2e2f36", "#55575f", "#8a8d96", "#e3b63b"),   # iron wax, gold hammer
}


def rgba(hex_):
    return tuple(int(hex_[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def texture(race):
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(SCROLL):
        for x, c in enumerate(row):
            if c in SCROLL_COLORS:
                img.putpixel((x, y), rgba(SCROLL_COLORS[c]))
    dark, wax, shine, emb = PALETTES[race]
    seal = {"D": dark, "S": wax, "H": shine}
    sx, sy = SEAL_AT
    for y, row in enumerate(SEAL):
        for x, c in enumerate(row):
            if c == "e":
                c = "E" if EMBLEMS[race][y - 2][x - 2] == "E" else "S"
                img.putpixel((sx + x, sy + y), rgba(emb if c == "E" else wax))
            elif c in seal:
                img.putpixel((sx + x, sy + y), rgba(seal[c]))
    for x, y in RIBBON:
        img.putpixel((x, y), rgba(wax))
    return img


def put_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))   # paths below are relative to the repo
    for race in PALETTES:
        png = f"{RP}/textures/item/contract/{race}.png"
        os.makedirs(os.path.dirname(png), exist_ok=True)
        texture(race).save(png)
        put_json(f"{RP}/models/item/contract/{race}.json",
                 {"parent": "minecraft:item/generated",
                  "textures": {"layer0": f"races:item/contract/{race}"}})
        put_json(f"{RP}/items/contract/{race}.json",
                 {"model": {"type": "minecraft:model", "model": f"races:item/contract/{race}"}})
        print("contract", race)

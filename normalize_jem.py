"""Force vanilla villager pivots on the top-level parts of a CEM .jem, without moving any geometry.

Why: EMF positions the named villager parts (head, body, arms, legs, ...) at their VANILLA pivots
but draws each part's boxes relative to the pivot written in the .jem. A model whose pivots differ
from vanilla is therefore drawn shifted by (vanilla - jem) per part. That is the "kobold renders too
high" bug: head +5, bodywear +16, arms +5, legs +4.

How: for a top-level part, box coordinates and first-level submodel translates are written in
absolute model space, and only the part's own `translate` (= -pivot) says where the pivot is.
For an unrotated part, rewriting just that `translate` to the vanilla value moves the pivot and
leaves every box where it was. A part with a static `rotate` (villager arms 43 deg, hat rim 90 deg;
these DO apply in game, a `"this.rx": 0` animation does not cancel them) turns around the pivot, so
its box coordinates and first-level child translates are also shifted by (I - R^-1)(new - old pivot)
to keep the rendered geometry identical. In the jem frame R = Rz(rz) * Ry(ry) * Rx(rx), degrees.

Necks: the head pivot is where vanilla turns, nods and shakes the head. A race whose head sits
lower than vanilla (NECK table) would swing its head around a point above its neck, so the head
"disconnects". For those, the head group (head, nose, headwear, headwear2; the game treats the
last three as children of the head) keeps its pivots at the race's own neck, and a `head.ty`
animation moves the game's head pivot down to that neck every frame. Vanilla head rotation then
happens around the neck, and the children follow because they hang off the head.
Legs of short races should hang off the body as submodels with their own hip pivot (see the dwarf).

Usage: python normalize_jem.py <file.jem> [more.jem ...]      (edits in place, idempotent)
"""
import json, math, sys

VANILLA = {
    "head": [0, -24, 0], "headwear": [0, -24, 0], "headwear2": [0, -24, 0],
    "body": [0, -24, 0], "bodywear": [0, -24, 0],
    "nose": [0, -26, 0],
    "arms": [0, -21.05, 1.05],
    "right_leg": [-2, -12, 0], "left_leg": [2, -12, 0],
}


# Hand-written animations that Blockbench may drop or that must stay authoritative.
# file name -> part -> {channel: expression}. These keys are (re)written every run; other keys are kept.
# Kobold tail: lazy idle sway driven by `age` (ticks), wider while walking (limb_speed 0..1).
# Root segment hangs ~70 deg down, so it swings on rz (pendulum); the children lie along their local z,
# so they bend on ry. Each segment lags the previous by 0.8 rad so the motion travels down the tail.
ANIMATIONS = {
    "villager7.jem": {"body": {
        "tail.rz": "torad(8 + 14 * limb_speed) * sin(age * 0.12)",
        "bone.ry": "torad(10 + 14 * limb_speed) * sin(age * 0.12 - 0.8)",
        "bone2.ry": "torad(12 + 16 * limb_speed) * sin(age * 0.12 - 1.6)",
    }},
}
# Neck height (jem y, px above the ground) of races whose head sits lower than vanilla (24).
NECK = {"villager2.jem": 20,   # hobbit
        "villager7.jem": 19,   # kobold
        "villager8.jem": 16}   # dwarf
HEAD_GROUP = ("head", "nose", "headwear", "headwear2")
# The game's model space has y pointing DOWN, so lowering the pivot is a positive ty change.
# If a head ever renders too high/low by twice its drop after this, flip this sign.
TY_SIGN = +1
for _file, _neck in NECK.items():
    ANIMATIONS.setdefault(_file, {}).setdefault("head", {})["head.ty"] = f"head.ty + {TY_SIGN * (24 - _neck)}"

STALE = {"tail.rx", "tail.ry", "tail.rz", "bone.rx", "bone.ry", "bone.rz", "bone2.rx", "bone2.ry", "bone2.rz"}


def apply_animations(path, model):
    import os
    wanted = ANIMATIONS.get(os.path.basename(path), {})
    changed = []
    for part in model.get("models", []):
        anims = wanted.get(part.get("part"))
        if not anims:
            continue
        blocks = part.setdefault("animations", [{}]) or [{}]
        part["animations"] = blocks
        before = json.dumps(blocks, sort_keys=True)
        for block in blocks:
            for key in [k for k in block if k in STALE]:
                del block[key]
        blocks[0].update(anims)
        if json.dumps(blocks, sort_keys=True) != before:
            changed.append(f"{part['part']}: animations set ({', '.join(anims)})")
    return changed


def rotation(deg):
    """3x3 matrix Rz * Ry * Rx for jem `rotate` degrees, in the jem (Blockbench) frame."""
    cx, cy, cz = (math.cos(math.radians(a)) for a in deg)
    sx, sy, sz = (math.sin(math.radians(a)) for a in deg)
    rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    mul = lambda a, b: [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return mul(rz, mul(ry, rx))


def compensation(rot, d):
    """(I - R^-1) d: what to add to absolute coords so geometry stays put when the pivot moves by d."""
    r = rotation(rot)
    rinv_d = [sum(r[k][i] * d[k] for k in range(3)) for i in range(3)]   # R^-1 = R^T
    return [d[i] - rinv_d[i] for i in range(3)]


def shift(vec, by):
    return [round(v + s, 5) + 0 for v, s in zip(vec, by)]   # +0 turns -0.0 into 0.0


def normalize(path):
    with open(path, encoding="utf-8") as f:
        model = json.load(f)
    changes, skipped = [], []
    import os
    drop = 24 - NECK.get(os.path.basename(path), 24)
    for part in model.get("models", []):
        name = part.get("part")
        want = VANILLA.get(name)
        if want is not None and name in HEAD_GROUP and drop:
            want = [want[0], want[1] + drop, want[2]]               # pivot lowered to the neck
        have = part.get("translate", [0, 0, 0])
        if want is None or [round(v, 4) for v in have] == want:
            continue
        rot = part.get("rotate", [0, 0, 0])
        if any(rot):
            d = [h - w for h, w in zip(have, want)]          # pivot = -translate
            c = compensation(rot, d)
            for box in part.get("boxes", []):
                box["coordinates"][:3] = shift(box["coordinates"][:3], c)
            for sub in part.get("submodels", []):
                sub["translate"] = shift(sub.get("translate", [0, 0, 0]), c)
        part["translate"] = want
        changes.append(f"{name}: {have} -> {want}" + (f" (rotated {rot}, coords shifted)" if any(rot) else ""))
    changes += apply_animations(path, model)
    # Texture pins: a race model must not lock a skin file. The model-level texture goes through
    # villager.png (ETF then picks the race's skin or one of its variants); part-level pins would
    # also force that skin onto the overlay layers, hiding profession overlays, so they are removed.
    if os.path.basename(path) != "villager.jem":
        vanilla_tex = "textures/entity/villager/villager.png"
        if model.get("texture") not in (None, vanilla_tex):
            changes.append(f"texture pin {model['texture']} -> {vanilla_tex}")
            model["texture"] = vanilla_tex

        def unpin(part):
            n = 1 if part.pop("texture", None) else 0
            return n + sum(unpin(s) for s in part.get("submodels", []))
        n = sum(unpin(p) for p in model.get("models", []))
        if n:
            changes.append(f"{n} part-level texture pin(s) removed")
    if changes:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(model, f, indent="\t")
            f.write("\n")
    print(f"{path}: {len(changes)} change(s)")
    for line in changes:
        print("   ", line)
    for line in skipped:
        print("    WARNING", line)
    return not skipped


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ok = all([normalize(p) for p in sys.argv[1:]])
    sys.exit(0 if ok else 1)

import json, os, re, shutil, sys, zipfile

SRC = sys.argv[1]          # extracted original pack (read-only use)
OUT = "server_resourcepack"
shutil.rmtree(OUT, ignore_errors=True)
shutil.copytree(SRC, OUT)

A = os.path.join(OUT, "assets/minecraft")
RAND = os.path.join(A, "optifine/random/entity/villager")
CEM = os.path.join(A, "optifine/cem")

def put(path, text):
    with open(path, "w", newline="\n") as f:
        f.write(text)

HDR = "# Matches the villager's scoreboard team (set by the races datapack). No names needed.\n"

# base skins: race -> texture index (villagerN.png)
BASE = [("race_hobbit", "2"), ("race_elf", "3"), ("race_copper_legs", "4"),
        ("race_copper_wheel", "5"), ("race_fishfolk", "6"), ("race_kobold", "7")]
put(os.path.join(RAND, "villager.properties"), HDR + "\n".join(
    f"skins.{n}={skin}\nteams.{n}={team}\n" for n, (team, skin) in enumerate(BASE, 1)))

# hobbit-only overlays (profession / type / profession_level) gated on the hobbit team
# Races whose overlays are switched OFF with a fully transparent texture (<name><skin>.png).
# To give a race real overlays later: replace that PNG and keep the rule.
from PIL import Image
BLANK = [("race_fishfolk", "6", (128, 128)), ("race_copper_wheel", "5", (128, 128)), ("race_kobold", "7", (64, 64))]   # (team, skin number, base texture size)

def blank_rules(extra_weights):
    out = ""
    for n, (team, skin, _) in enumerate(BLANK, 2):
        out += f"\nskins.{n}={skin}\n" + ("weights.%d=100\n" % n if extra_weights else "") + f"teams.{n}={team}\n"
    return out

for sub in ("profession", "type", "profession_level"):
    lvl = (sub == "profession_level")
    for fn in os.listdir(os.path.join(RAND, sub)):
        if not fn.endswith(".properties"):
            continue
        base = fn[:-len(".properties")]
        hob = "skins.1=2\n" + ("weights.1=100\n" if lvl else "") + "teams.1=race_hobbit\n"
        put(os.path.join(RAND, sub, fn), HDR + hob + blank_rules(lvl))
        for team, skin, size in BLANK:
            Image.new("RGBA", size, (0, 0, 0, 0)).save(os.path.join(RAND, sub, f"{base}{skin}.png"))

# kobold base texture must also exist in the random folder
shutil.copy(os.path.join(A, "textures/entity/villager/villager7.png"),
            os.path.join(RAND, "villager7.png"))

# CEM: model N -> villagerN.jem
put(os.path.join(CEM, "villager.properties"), HDR + "\n".join(
    f"models.{n}={skin}\nteams.{n}={team}\n" for n, (team, skin) in enumerate(BASE, 1)))

# latest hand-edited models from this conversation (wheel anim, kobold tail anim + per-part textures)
shutil.copy("villager5.jem", os.path.join(CEM, "villager5.jem"))
shutil.copy("villager7.jem", os.path.join(CEM, "villager7.jem"))

# kobold jem pointed at a texture that does not exist
p = os.path.join(CEM, "villager7.jem")
txt = open(p).read()
txt = txt.replace("fantasyraces:textures/entity/villager/kobold.png",
                  "textures/entity/villager/villager7.png")
put(p, txt)
json.loads(txt)

# Blockbench exports custom pivots; EMF uses vanilla ones. Re-normalize every build.
from normalize_jem import normalize
for n in range(2, 8):
    normalize(os.path.join(CEM, f"villager{n}.jem"))

with zipfile.ZipFile("fantasyraces_resourcepack.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for d, _, files in os.walk(OUT):
        for f in files:
            fp = os.path.join(d, f)
            z.write(fp, os.path.relpath(fp, OUT))
print("rp ok")

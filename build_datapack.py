import json, os, shutil, zipfile

os.chdir(os.path.dirname(os.path.abspath(__file__)))   # paths below are relative to the repo

ROOT = "server_datapack"
NS = "races"

# id, display name, recipe ingredients (placeholders except hobbit; change freely)
RACES = [
    ("hobbit",       "Hobbit",           ["paper", "wheat", "fern"]),
    ("elf",          "Elf",              ["paper", "lily_of_the_valley", "glow_berries"]),
    ("copper",       "Copper Construct", ["paper", "copper_ingot", "redstone"]),
    ("fishfolk",     "Fishfolk",         ["paper", "kelp", "cod"]),
    ("kobold",       "Kobold",           ["paper", "pointed_dripstone", "coal"]),
    ("dwarf",        "Dwarf",            ["paper", "gold_ingot", "cobbled_deepslate"]),
]
ALL_IDS = [r[0] for r in RACES]
# What the resource pack matches (one team per look). Copper is one race with two looks.
# Copper constructs weather like copper blocks: one team per look AND stage (keep in sync with race_teams.py).
STAGES = ["", "_exposed", "_weathered", "_oxidized"]
TEAMS = ["hobbit", "elf"] + [f"copper_{l}{s}" for l in ("legs", "wheel") for s in STAGES] + ["fishfolk", "kobold", "dwarf"]
# Tags: the races plus the two copper looks, and the copper wax state.
TAGS = ["hobbit", "elf", "copper", "copper_legs", "copper_wheel", "copper_waxed", "fishfolk", "kobold", "dwarf"]

shutil.rmtree(ROOT, ignore_errors=True)

def w(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", newline="\n") as f:
        f.write(content if isinstance(content, str) else json.dumps(content, indent=2) + "\n")

# ---- pack.mcmeta ---------------------------------------------------------
# 26.3 data pack format per community docs; verify against your server log.
w("pack.mcmeta", {"pack": {"description": "Folk & Forge: folks (fantasy races), contracts, copper weathering",
                           "min_format": 121, "max_format": 121}})

# ---- load: create one scoreboard team per race ---------------------------
# ETF/EMF can read a villager's scoreboard TEAM client-side (tags are server-only).
w("data/minecraft/tags/function/load.json", {"values": [f"{NS}:load"]})
w(f"data/{NS}/function/load.mcfunction",
  "# Teams are the client-visible marker the resource pack matches with teams.N=race_<id>\n" +
  "".join(f"team add race_{i}\n" for i in TEAMS) +
  "scoreboard objectives add races.copper dummy\n"
  "schedule function races:copper/tick 1200t replace\n")

# ---- set functions (run AS the villager; also usable by ops) -------------
#   /execute as @e[type=villager,distance=..30] run function races:set/hobbit
clear_tags = "".join(f"tag @s remove race_{i}\n" for i in TAGS)
FX = ("execute at @s run playsound minecraft:entity.villager.celebrate neutral @a ~ ~ ~ 1 1\n"
      "execute at @s run particle minecraft:happy_villager ~ ~1 ~ 0.3 0.4 0.3 0 12\n")

def set_fn(look, race_tag):
    # look = team/texture/model variant; race_tag = the race tag for trade gating
    extra = f"tag @s add race_{race_tag}\n" if race_tag != look else ""
    w(f"data/{NS}/function/set/{look}.mcfunction",
      f"# Make this villager look like: {look}.\n{clear_tags}{extra}"
      f"tag @s add race_{look}\n" +
      ("scoreboard players set @s races.copper 0\nfunction races:copper/team\n" if race_tag == "copper"
       else f"team join race_{look} @s\n") + FX)

for look in ["hobbit", "elf", "fishfolk", "kobold", "dwarf"]:
    set_fn(look, look)
set_fn("copper_legs", "copper")
set_fn("copper_wheel", "copper")

# Copper Construct: random look, rolled ONCE (model and texture always agree).
w(f"data/{NS}/predicate/coin_flip.json", {"type": "minecraft:random_chance", "chance": 0.5})
w(f"data/{NS}/function/set/copper.mcfunction",
  "# Random copper look. Legs on a win; otherwise wheel.\n"
  "# Clear the legs tag first, or an already-legged villager could never roll wheel.\n"
  "tag @s remove race_copper_legs\n"
  "execute if predicate races:coin_flip run function races:set/copper_legs\n"
  "execute unless entity @s[tag=race_copper_legs] run function races:set/copper_wheel\n")

# ---- copper weathering --------------------------------------------------
# Stage 0..3 (copper, exposed, weathered, oxidized) lives in the races.copper score and is shown by
# the per-stage team (the resource pack matches teams). Every minute each unwaxed construct has a
# 1-in-60 chance to age one stage (about an hour per stage of loaded time, like copper blocks).
# Honeycomb waxes (freezes the stage); an axe removes wax, or scrapes one stage off if unwaxed.
w(f"data/{NS}/predicate/copper_age_chance.json", {"type": "minecraft:random_chance", "chance": 1 / 60})
w(f"data/{NS}/function/copper/tick.mcfunction",
  "# Runs every 1200 ticks (scheduled from races:load).\n"
  "# Constructs converted before weathering existed start at stage 0.\n"
  "execute as @e[type=minecraft:villager,tag=race_copper] unless score @s races.copper matches 0.. "
  "run function races:copper/set_copper\n"
  "execute as @e[type=minecraft:villager,tag=race_copper,tag=!race_copper_waxed] "
  "if score @s races.copper matches ..2 if predicate races:copper_age_chance run function races:copper/age\n"
  "schedule function races:copper/tick 1200t replace\n")
w(f"data/{NS}/function/copper/age.mcfunction",
  "scoreboard players add @s races.copper 1\nfunction races:copper/team\n")
w(f"data/{NS}/function/copper/team.mcfunction",
  "# Runs as a copper construct: join the team for its look and weathering stage.\n" +
  "".join(f"execute if entity @s[tag=race_copper_{look}] if score @s races.copper matches {i} "
          f"run team join race_copper_{look}{st} @s\n"
          for look in ("legs", "wheel") for i, st in enumerate(STAGES)))


def copper_click(name, items, reward):
    """Right-click a copper construct holding `items` -> run `reward` lines (player context)."""
    w(f"data/{NS}/advancement/copper/{name}.json", {
        "criteria": {"use": {
            "trigger": "minecraft:player_interacted_with_entity",
            "conditions": {
                "item": {"items": items},
                "entity": {"type": "minecraft:entity_properties", "entity": "this",
                           "predicate": {"minecraft:entity_type": "minecraft:villager",
                                         "minecraft:entity_tags": {"all_of": ["race_copper"]}}}}}},
        "rewards": {"function": f"{NS}:copper/{name}"}})
    w(f"data/{NS}/function/copper/{name}.mcfunction",
      "# Runs as the player who right-clicked a copper construct.\n"
      f"advancement revoke @s only races:copper/{name}\n"
      "tag @e[type=minecraft:villager,tag=race_copper,distance=..6,sort=nearest,limit=1] add race_pending\n"
      + reward +
      "tag @e[type=minecraft:villager,tag=race_pending] remove race_pending\n")


copper_click("wax", "minecraft:honeycomb",
  "execute if entity @e[type=minecraft:villager,tag=race_pending,tag=!race_copper_waxed,limit=1] "
  "unless entity @s[gamemode=creative] run clear @s minecraft:honeycomb 1\n"
  "execute as @e[type=minecraft:villager,tag=race_pending,tag=!race_copper_waxed,limit=1] at @s "
  "run function races:copper/wax_on\n")
w(f"data/{NS}/function/copper/wax_on.mcfunction",
  "tag @s add race_copper_waxed\n"
  "particle minecraft:wax_on ~ ~1 ~ 0.4 0.6 0.4 0 12\n"
  "playsound minecraft:item.honeycomb.wax_on neutral @a ~ ~ ~ 1 1\n")
copper_click("scrape", "#minecraft:axes",
  "execute as @e[type=minecraft:villager,tag=race_pending,limit=1] at @s run function races:copper/scrape_one\n")
w(f"data/{NS}/function/copper/scrape_one.mcfunction",
  "# Wax comes off first; otherwise scrape one weathering stage.\n"
  "execute if entity @s[tag=race_copper_waxed] run return run function races:copper/wax_off\n"
  "execute if score @s races.copper matches 1.. run function races:copper/scraped\n")
w(f"data/{NS}/function/copper/wax_off.mcfunction",
  "tag @s remove race_copper_waxed\n"
  "particle minecraft:wax_off ~ ~1 ~ 0.4 0.6 0.4 0 12\n"
  "playsound minecraft:item.axe.wax_off neutral @a ~ ~ ~ 1 1\n")
w(f"data/{NS}/function/copper/scraped.mcfunction",
  "scoreboard players remove @s races.copper 1\nfunction races:copper/team\n"
  "particle minecraft:scrape ~ ~1 ~ 0.4 0.6 0.4 0 12\n"
  "playsound minecraft:item.axe.scrape neutral @a ~ ~ ~ 1 1\n")
# Ops: /execute as @e[type=villager,tag=race_copper,distance=..10] run function races:copper/set_oxidized
for i, st in enumerate(["copper", "exposed", "weathered", "oxidized"]):
    w(f"data/{NS}/function/copper/set_{st}.mcfunction",
      f"# Ops: force a weathering stage.\nscoreboard players set @s races.copper {i}\nfunction races:copper/team\n")

# ---- per-race: contract / give / recipe ----------------------------------
for rid, name, ing in RACES:
    item_comps = (f'item_name="{name} Contract",'
                  f'lore=["Right-click an unemployed villager","to make them a {name.lower()}."],'
                  f'custom_data={{race_contract:"{rid}"}},enchantment_glint_override=true,'
                  f'item_model="races:contract/{rid}"')   # texture: build_contract_textures.py
    w(f"data/{NS}/function/give/{rid}_contract.mcfunction",
      f"# /function races:give/{rid}_contract  (ops only)\n"
      f"give @s minecraft:paper[{item_comps}] 1\n")

    w(f"data/{NS}/advancement/contract/{rid}.json", {
        "criteria": {"use_contract": {
            "trigger": "minecraft:player_interacted_with_entity",
            "conditions": {
                "item": {"items": "minecraft:paper",
                         "predicates": {"minecraft:custom_data": {"race_contract": rid}}},
                "entity": {"type": "minecraft:entity_properties", "entity": "this",
                           "predicate": {"minecraft:entity_type": "minecraft:villager"}}
            }}},
        "rewards": {"function": f"{NS}:contract/apply_{rid}"}
    })

    w(f"data/{NS}/function/contract/apply_{rid}.mcfunction",
      f"# Runs as the player who right-clicked a villager with a {name} Contract.\n"
      f"advancement revoke @s only races:contract/{rid}\n"
      f"tag @e[type=minecraft:villager,distance=..6,sort=nearest,limit=1] add race_pending\n"
      f'execute if entity @e[type=minecraft:villager,tag=race_pending,limit=1] run clear @s minecraft:paper[minecraft:custom_data~{{race_contract:"{rid}"}}] 1\n'
      f"execute as @e[type=minecraft:villager,tag=race_pending,limit=1] run function races:set/{rid}\n"
      f"tag @e[type=minecraft:villager,tag=race_pending] remove race_pending\n")

    w(f"data/{NS}/recipe/{rid}_contract.json", {
        "type": "minecraft:crafting_shapeless",
        "category": "misc",
        "ingredients": [f"minecraft:{i}" for i in ing],
        "result": {"id": "minecraft:paper", "count": 1, "components": {
            "minecraft:item_name": f"{name} Contract",
            "minecraft:lore": ["Right-click an unemployed villager", f"to make them a {name.lower()}."],
            "minecraft:custom_data": {"race_contract": rid},
            "minecraft:enchantment_glint_override": True,
            "minecraft:item_model": f"races:contract/{rid}"}}
    })

# Reset a villager back to vanilla look
w(f"data/{NS}/function/set/clear.mcfunction",
  "# Runs as the villager: remove any race.\n" + clear_tags + "scoreboard players reset @s races.copper\nteam leave @s\n")

# Unlock all contract recipes once the player holds paper
w(f"data/{NS}/advancement/recipe/unlock_contracts.json", {
    "criteria": {"has_paper": {"trigger": "minecraft:inventory_changed",
                               "conditions": {"items": [{"items": "minecraft:paper"}]}}},
    "rewards": {"recipes": [f"{NS}:{i}_contract" for i in ALL_IDS]}
})

# ---- trades (hobbit only for now; gated on the server-side tag) ----------
GATE = {"type": "minecraft:entity_properties", "entity": "this",
        "predicate": {"minecraft:entity_tags": {"all_of": ["race_hobbit"]}}}

def trade(name, wants, wcount, gives, gcount, uses, xp):
    w(f"data/{NS}/villager_trade/hobbit/{name}.json", {
        "wants": {"id": f"minecraft:{wants}", "count": wcount},
        "gives": {"id": f"minecraft:{gives}", "count": gcount},
        "max_uses": uses, "xp": xp, "merchant_predicate": GATE})
    return f"{NS}:hobbit/{name}"

pools = {
    ("farmer", 1): [trade("farmer_potatoes","potato",24,"emerald",1,16,2),
                    trade("farmer_pie","emerald",1,"pumpkin_pie",3,12,2),
                    trade("farmer_baked","emerald",1,"baked_potato",8,16,2)],
    ("farmer", 2): [trade("farmer_carrots","carrot",22,"emerald",1,16,5),
                    trade("farmer_elevenses","emerald",1,"cookie",12,16,5)],
    ("farmer", 3): [trade("farmer_mushrooms","brown_mushroom",14,"emerald",1,16,10),
                    trade("farmer_mead","emerald",2,"honey_bottle",2,12,10)],
    ("farmer", 4): [trade("farmer_apples","apple",12,"emerald",1,16,15),
                    trade("farmer_cake","emerald",3,"cake",1,8,15)],
    ("fisherman", 1): [trade("fisher_cod","cod",15,"emerald",1,16,2),
                       trade("fisher_cooked_cod","emerald",1,"cooked_cod",6,16,2)],
    ("fisherman", 2): [trade("fisher_salmon","salmon",13,"emerald",1,16,5),
                       trade("fisher_cooked_salmon","emerald",1,"cooked_salmon",6,16,5)],
}
for (prof, lvl), values in pools.items():
    w(f"data/minecraft/tags/villager_trade/{prof}/level_{lvl}.json", {"replace": False, "values": values})

# ---- README --------------------------------------------------------------
rows = "\n".join(f"| {n} | `race_{i}`" + (" (random `race_copper_legs` / `race_copper_wheel`)" if i == "copper" else "") +
                 f" | `/function races:give/{i}_contract` | {' + '.join(g)} |"
                 for i, n, g in RACES)
w("README.md", f"""# Folk & Forge datapack: Folks (fantasy races)

Each race = a scoreboard team `race_<id>` (read by ETF/EMF in the resource pack)
plus a tag `race_<id>` (read by datapack trade gating). Nothing is renamed.

| Race | Team/tag | Give | Craft (shapeless) |
|---|---|---|---|
{rows}

## Use
1. Craft or `/function races:give/<race>_contract`.
2. Right-click an UNEMPLOYED villager (stand within a few blocks).
3. Give it a workstation afterward; trades roll at job claim / level-up.

## Converting existing villagers (op)
Stand in the village:
`/execute as @e[type=villager,distance=..40] run function races:set/hobbit`
Copper constructs: `races:set/copper` rolls legs or wheel at random; `races:set/copper_legs` and `races:set/copper_wheel` force one.
Reset to vanilla: `... run function races:set/clear`

## Copper weathering
Copper constructs age one stage (exposed, weathered, oxidized) about every hour of loaded time.
Right-click with honeycomb to wax (freezes the stage); with an axe to remove wax or scrape one stage off.
Ops: `... run function races:copper/set_<copper|exposed|weathered|oxidized>`.

Only hobbits have custom trades so far. Recipes for non-hobbit races are placeholders.
""")

os.makedirs("dist", exist_ok=True)
with zipfile.ZipFile("dist/races_datapack.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for d, _, files in os.walk(ROOT):
        for f in files:
            p = os.path.join(d, f)
            z.write(p, os.path.relpath(p, ROOT))
print("datapack ok")

"""Race voices for villagers through Entity Sound Features (client mod; needs ETF, and EMF for the models).

ESF picks a sound per entity with ETF-style rules, so the race teams the datapack sets select the
voice, like they select skins and models:
    assets/minecraft/esf/entity/villager/<event>.properties   rules: sounds.N=<k> + teams.N=<team>
    assets/minecraft/esf/entity/villager/<event><k>.json      the sounds for variant k (sounds.json format)
The last rule `sounds.N=1` keeps vanilla sounds for every other villager (suffix 1 = vanilla).
Babies use the same events; the game raises their pitch itself.
All sounds are vanilla .ogg files re-used with new pitch/volume, so nothing extra is shipped.
Players without ESF just hear normal villagers.

Usage: python build_sounds.py [path/to/26.3.json version file]      (checks every file exists)
"""
import json, os, sys
import race_teams

ESF = "server_resourcepack/assets/minecraft/esf/entity/villager"
EVENTS = ["ambient", "yes", "no", "trade", "hurt", "death", "celebrate"]
HDR = "# Race voices (Entity Sound Features). Matches the villager's team set by the races datapack.\n"


def s(path, *nums, pitch=1.0, volume=1.0):
    """Sound entries for mob/<path><n>.ogg (or mob/<path>.ogg when no numbers)."""
    names = [f"{path}{n}" for n in nums] if nums else [path]
    return [{"name": f"minecraft:mob/{n}", "pitch": pitch, "volume": volume} for n in names]


V = "villager/"
VOICES = {
    # hobbit: cheerful, higher villager voice
    2: dict(ambient=s(V + "idle", 1, 2, 3, pitch=1.25), yes=s(V + "yes", 1, 2, 3, pitch=1.25), no=s(V + "no", 1, 2, 3, pitch=1.25),
            trade=s(V + "haggle", 1, 2, 3, pitch=1.25), hurt=s(V + "hit", 1, 2, 3, 4, pitch=1.25), death=s(V + "death", pitch=1.25),
            celebrate=s(V + "yes", 1, 2, 3, pitch=1.4)),
    # elf: the lighter wandering-trader voice, allay chimes when celebrating
    3: dict(ambient=s("wandering_trader/idle", 1, 2, 3, 4, 5, pitch=1.1), yes=s("wandering_trader/yes", 1, 2, 3, 4, pitch=1.1),
            no=s("wandering_trader/no", 1, 2, 3, 4, 5, pitch=1.1), trade=s("wandering_trader/haggle", 1, 2, 3, pitch=1.1),
            hurt=s("wandering_trader/hurt", 1, 2, 3, 4, pitch=1.1), death=s("wandering_trader/death", pitch=1.1),
            celebrate=s("allay/item_given", 1, 2, 3, 4, volume=0.8)),
    # fishfolk: axolotl chirps, dolphin clicks, frog croaks
    6: dict(ambient=s("axolotl/idle_air", 1, 2, 3, 4, 5) + s("frog/idle", 1, 2, 3, 4, pitch=1.2, volume=0.7),
            yes=s("dolphin/play", 1, 2), no=s("dolphin/blowhole", 1, 2, volume=0.8), trade=s("axolotl/idle_air", 1, 2, 3, pitch=0.85),
            hurt=s("axolotl/hurt", 1, 2, 3, 4), death=s("axolotl/death", 1, 2), celebrate=s("dolphin/jump", 1, 2, 3, volume=0.8)),
    # kobold: yips, sniffs and hisses
    7: dict(ambient=s("fox/idle", 1, 2, 3, 4, 5, 6, pitch=1.15) + s("fox/sniff", 1, 2, 3, 4, pitch=1.2) + s("silverfish/say", 1, 2, pitch=0.8, volume=0.5),
            yes=s("fox/sniff", 1, 2, 3, 4, pitch=1.3), no=s("fox/spit", 1, 2, 3, pitch=1.2), trade=s("fox/eat", 1, 2, 3, pitch=1.15),
            hurt=s("fox/hurt", 1, 2, 3, 4, pitch=1.15), death=s("fox/death", 1, 2, pitch=1.1), celebrate=s("fox/screech", 1, 2, 3, 4, pitch=1.2, volume=0.6)),
    # dwarf: deep villager voice
    8: dict(ambient=s(V + "idle", 1, 2, 3, pitch=0.75), yes=s(V + "yes", 1, 2, 3, pitch=0.75), no=s(V + "no", 1, 2, 3, pitch=0.75),
            trade=s(V + "haggle", 1, 2, 3, pitch=0.75), hurt=s(V + "hit", 1, 2, 3, 4, pitch=0.8), death=s(V + "death", pitch=0.75),
            celebrate=s(V + "yes", 1, 2, 3, pitch=0.85)),
}


def copper_voice(stage_folder):
    """Copper constructs whirr and beep; hurt/death sound like a copper golem of the same weathering."""
    g = f"coppergolem/{stage_folder}/"
    return dict(ambient=s(g + "spin", 1, 2, 3, 4, 5, 6, 7, volume=0.5), yes=s("coppergolem/item_drop"),
                no=s("coppergolem/no_item_no_get"), trade=s("coppergolem/item_no_drop") + s(g + "spin", 1, 2, volume=0.6),
                hurt=s(g + "hurt", 1, 2, 3, 4), death=s(g + "death"), celebrate=s("coppergolem/spawn", volume=0.8))


# copper voice numbers: 4 = regular (copper + exposed), 41 = weathered, 42 = oxidized
VOICES.update({4: copper_voice("regular"), 41: copper_voice("weathered"), 42: copper_voice("oxidized")})
STAGE_VOICE = {"": 4, "_exposed": 4, "_weathered": 41, "_oxidized": 42}
RULES = [(2, "race_hobbit"), (3, "race_elf")] + \
    [(k, " ".join(f"{look}{st}" for look in race_teams.COPPER_LOOKS for st, v in STAGE_VOICE.items() if v == k)) for k in (4, 41, 42)] + \
    [(6, "race_fishfolk"), (7, "race_kobold"), (8, "race_dwarf")]


def check_files(version_json):
    """Every referenced .ogg must exist in the game's asset index."""
    with open(version_json) as f:
        idx_id = json.load(f)["assetIndex"]["id"]
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(version_json))), "assets", "indexes", f"{idx_id}.json")) as f:
        objects = json.load(f)["objects"]
    missing = sorted({e["name"] for v in VOICES.values() for es in v.values() for e in es
                      if f"minecraft/sounds/{e['name'].split(':', 1)[1]}.ogg" not in objects})
    return missing


def main():
    version_json = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.expandvars(r"%APPDATA%\.minecraft\versions\26.3\26.3.json")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))   # paths below are relative to the repo
    missing = check_files(version_json)
    if missing:
        sys.exit(f"these sounds do not exist in this game version: {missing}")
    os.makedirs(ESF, exist_ok=True)
    for ev in EVENTS:
        for k, voice in VOICES.items():
            with open(f"{ESF}/{ev}{k}.json", "w", encoding="utf-8", newline="\n") as f:
                json.dump({"sounds": voice[ev]}, f, indent="\t")
        rules = RULES + [(1, None)]                      # last rule: everyone else keeps vanilla
        with open(f"{ESF}/{ev}.properties", "w", encoding="utf-8", newline="\n") as f:
            f.write(HDR + "".join(f"\nsounds.{i}={k}\n" + (f"teams.{i}={t}\n" if t else "")
                                  for i, (k, t) in enumerate(rules, 1)))
    print(f"{len(EVENTS)} villager sound events x {len(VOICES)} race voices written (all sound files found)")


if __name__ == "__main__":
    main()

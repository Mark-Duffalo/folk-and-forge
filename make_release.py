"""Package the resource pack and datapack as release zips (and optionally publish a GitHub release).

    python make_release.py                     # build dist/ zips, version = today's date
    python make_release.py 1.2.0               # build with an explicit version
    python make_release.py 1.2.0 --publish     # also create GitHub release v1.2.0 with both zips (needs `gh`)

The zips keep the same file names in every release, so these links always point at the newest one:
    https://github.com/Mark-Duffalo/fantasy-races/releases/latest/download/FantasyRaces-ResourcePack.zip
    https://github.com/Mark-Duffalo/fantasy-races/releases/latest/download/FantasyRaces-Datapack.zip
The resource pack's SHA-1 is printed for server.properties (resource-pack-sha1); update it with
each release, or players keep a cached old pack.

Before zipping, the packs are checked: pack.mcmeta present, every JSON/.jem parses, and every
ETF/EMF/ESF rule points at a file that exists. Editor/OS clutter (desktop.ini, Blockbench
.bbmodel sources, *.old backups) is left out of the zips.
"""
import datetime, glob, hashlib, json, os, re, subprocess, sys, zipfile

os.chdir(os.path.dirname(os.path.abspath(__file__)))
PACKS = {"FantasyRaces-ResourcePack.zip": "server_resourcepack", "FantasyRaces-Datapack.zip": "server_datapack"}
SKIP_NAMES = {"desktop.ini", "thumbs.db", ".ds_store"}
SKIP_EXT = (".bbmodel", ".old", ".bak", ".psd", ".kra", ".xcf")


def included(path):
    name = os.path.basename(path).lower()
    return name not in SKIP_NAMES and not name.endswith(SKIP_EXT)


def check(root):
    problems = []
    if not os.path.isfile(f"{root}/pack.mcmeta"):
        problems.append(f"{root}/pack.mcmeta missing")
    for f in glob.glob(f"{root}/**/*", recursive=True):
        if f.endswith((".json", ".jem", ".mcmeta")) and included(f):
            try:
                json.load(open(f, encoding="utf-8"))
            except Exception as e:
                problems.append(f"{f}: {e}")
    for prop in glob.glob(f"{root}/**/*.properties", recursive=True):
        base, folder = os.path.basename(prop)[:-len(".properties")], os.path.dirname(prop)
        text = open(prop, encoding="utf-8").read()
        for key, nums in re.findall(r"^(skins|models|sounds)\.\d+=(.*)$", text, flags=re.M):
            for n in nums.split():
                if key == "sounds" and n in ("0", "1"):
                    continue                      # ESF: 0/1 mean the vanilla sound
                ext = {"skins": [".png"], "models": [".jem"], "sounds": [".json", ".ogg"]}[key]
                if not any(os.path.exists(f"{folder}/{base}{n}{e}") for e in ext):
                    problems.append(f"{prop}: {key} {n} has no file")
    return problems


def build_zip(root, out):
    files = sorted(f for f in glob.glob(f"{root}/**/*", recursive=True) if os.path.isfile(f) and included(f))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, os.path.relpath(f, root).replace(os.sep, "/"))
    return len(files)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    version = args[0] if args else datetime.date.today().strftime("%Y.%m.%d")
    publish = "--publish" in sys.argv
    problems = [p for root in PACKS.values() for p in check(root)]
    if problems:
        sys.exit("Not releasing, fix these first:\n  " + "\n  ".join(problems))
    os.makedirs("dist", exist_ok=True)
    for name, root in PACKS.items():
        n = build_zip(root, f"dist/{name}")
        sha1 = hashlib.sha1(open(f"dist/{name}", "rb").read()).hexdigest()
        print(f"dist/{name}: {n} files, {os.path.getsize(f'dist/{name}') // 1024} KB, sha1 {sha1}")
    if publish:
        tag = f"v{version}"
        notes = (f"Fantasy Races {version}.\n\nResource pack: needs Entity Texture Features + Entity Model Features "
                 f"(and Entity Sound Features for race voices). Datapack: put in the world's datapacks folder and /reload.")
        subprocess.run(["gh", "release", "create", tag, *[f"dist/{n}" for n in PACKS], "--title", f"Fantasy Races {version}",
                        "--notes", notes], check=True)
        print(f"published {tag}")
    else:
        print(f"Version {version} built. To publish: python make_release.py {version} --publish")


if __name__ == "__main__":
    main()

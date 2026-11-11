"""Shared team names for the resource-pack generators.

Copper constructs weather like copper blocks. The datapack tracks the stage and moves the villager
to a per-stage team (ETF only sees teams), so the pack needs:
  - base skins: one rule per stage team (race_copper_legs -> 4, ..._exposed -> 401, ...)
  - models and overlays: one rule whose teams.N lists all four stage teams of a look.
Keep COPPER_STAGES in sync with build_datapack.py.
"""
import re

COPPER_STAGES = ["", "_exposed", "_weathered", "_oxidized"]
COPPER_LOOKS = ["race_copper_legs", "race_copper_wheel"]


def copper_teams(look):
    return " ".join(look + s for s in COPPER_STAGES)


def expand_copper(path):
    """Rewrite `teams.N=race_copper_legs` (single team) to the four stage teams. Idempotent."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    new = re.sub(r"^(teams\.\d+=)(race_copper_(?:legs|wheel))[ \t]*$", lambda m: m.group(1) + copper_teams(m.group(2)),
                 text, flags=re.M)
    if new != text:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)
        return True
    return False

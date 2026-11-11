# Races datapack

Each race = a scoreboard team `race_<id>` (read by ETF/EMF in the resource pack)
plus a tag `race_<id>` (read by datapack trade gating). Nothing is renamed.

| Race | Team/tag | Give | Craft (shapeless) |
|---|---|---|---|
| Hobbit | `race_hobbit` | `/function races:give/hobbit_contract` | paper + wheat + fern |
| Elf | `race_elf` | `/function races:give/elf_contract` | paper + lily_of_the_valley + glow_berries |
| Copper Construct | `race_copper` (random `race_copper_legs` / `race_copper_wheel`) | `/function races:give/copper_contract` | paper + copper_ingot + redstone |
| Fishfolk | `race_fishfolk` | `/function races:give/fishfolk_contract` | paper + kelp + cod |
| Kobold | `race_kobold` | `/function races:give/kobold_contract` | paper + pointed_dripstone + coal |
| Dwarf | `race_dwarf` | `/function races:give/dwarf_contract` | paper + gold_ingot + cobbled_deepslate |

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

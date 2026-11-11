# Runs every 1200 ticks (scheduled from races:load).
# Constructs converted before weathering existed start at stage 0.
execute as @e[type=minecraft:villager,tag=race_copper] unless score @s races.copper matches 0.. run function races:copper/set_copper
execute as @e[type=minecraft:villager,tag=race_copper,tag=!race_copper_waxed] if score @s races.copper matches ..2 if predicate races:copper_age_chance run function races:copper/age
schedule function races:copper/tick 1200t replace

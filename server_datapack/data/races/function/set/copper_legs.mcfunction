# Make this villager look like: copper_legs.
tag @s remove race_hobbit
tag @s remove race_elf
tag @s remove race_copper
tag @s remove race_copper_legs
tag @s remove race_copper_wheel
tag @s remove race_copper_waxed
tag @s remove race_fishfolk
tag @s remove race_kobold
tag @s remove race_dwarf
tag @s add race_copper
tag @s add race_copper_legs
scoreboard players set @s races.copper 0
function races:copper/team
execute at @s run playsound minecraft:entity.villager.celebrate neutral @a ~ ~ ~ 1 1
execute at @s run particle minecraft:happy_villager ~ ~1 ~ 0.3 0.4 0.3 0 12

# Runs as the player who right-clicked a copper construct.
advancement revoke @s only races:copper/wax
tag @e[type=minecraft:villager,tag=race_copper,distance=..6,sort=nearest,limit=1] add race_pending
execute if entity @e[type=minecraft:villager,tag=race_pending,tag=!race_copper_waxed,limit=1] unless entity @s[gamemode=creative] run clear @s minecraft:honeycomb 1
execute as @e[type=minecraft:villager,tag=race_pending,tag=!race_copper_waxed,limit=1] at @s run function races:copper/wax_on
tag @e[type=minecraft:villager,tag=race_pending] remove race_pending

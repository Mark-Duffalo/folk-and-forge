# Runs as the player who right-clicked a copper construct.
advancement revoke @s only races:copper/scrape
tag @e[type=minecraft:villager,tag=race_copper,distance=..6,sort=nearest,limit=1] add race_pending
execute as @e[type=minecraft:villager,tag=race_pending,limit=1] at @s run function races:copper/scrape_one
tag @e[type=minecraft:villager,tag=race_pending] remove race_pending

# Runs as the player who right-clicked a villager with a Copper Construct Contract.
advancement revoke @s only races:contract/copper
tag @e[type=minecraft:villager,distance=..6,sort=nearest,limit=1] add race_pending
execute if entity @e[type=minecraft:villager,tag=race_pending,limit=1] run clear @s minecraft:paper[minecraft:custom_data~{race_contract:"copper"}] 1
execute as @e[type=minecraft:villager,tag=race_pending,limit=1] run function races:set/copper
tag @e[type=minecraft:villager,tag=race_pending] remove race_pending

# Random copper look. Legs on a win; otherwise wheel.
# Clear the legs tag first, or an already-legged villager could never roll wheel.
tag @s remove race_copper_legs
execute if predicate races:coin_flip run function races:set/copper_legs
execute unless entity @s[tag=race_copper_legs] run function races:set/copper_wheel

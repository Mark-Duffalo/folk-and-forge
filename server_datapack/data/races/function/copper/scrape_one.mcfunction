# Wax comes off first; otherwise scrape one weathering stage.
execute if entity @s[tag=race_copper_waxed] run return run function races:copper/wax_off
execute if score @s races.copper matches 1.. run function races:copper/scraped

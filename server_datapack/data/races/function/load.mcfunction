# Teams are the client-visible marker the resource pack matches with teams.N=race_<id>
team add race_hobbit
team add race_elf
team add race_copper_legs
team add race_copper_legs_exposed
team add race_copper_legs_weathered
team add race_copper_legs_oxidized
team add race_copper_wheel
team add race_copper_wheel_exposed
team add race_copper_wheel_weathered
team add race_copper_wheel_oxidized
team add race_fishfolk
team add race_kobold
team add race_dwarf
scoreboard objectives add races.copper dummy
schedule function races:copper/tick 1200t replace

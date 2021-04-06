# -*- coding: utf-8 -*-

# pip install -r requirements.txt

from astrobox.space_field import SpaceField
from tranova import TranovaDrone
from stage_03_harvesters.reaper import ReaperDrone
from stage_03_harvesters.driller import DrillerDrone

number_of_drones = 5

if __name__ == '__main__':
    scene = SpaceField(
        speed=4,
        asteroids_count=20,
    )
    team_1 = [TranovaDrone() for i in range(number_of_drones)]
    team_2 = [DrillerDrone() for i in range(number_of_drones)]
    scene.go()

# Первый этап: зачёт!
# Второй этап: зачёт!

# Победы 6/11
# Третий этап: зачёт!

# -*- coding: utf-8 -*-
import datetime
from random import choice
from astrobox.core import Drone


class TranovaDrone(Drone):
    my_team = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.my_asteroids = []

        self.distance_flown_full = 0
        self.distance_flown_partially_loaded = 0
        self.distance_flown_empty = 0

        self.operation = ()
        self.last_task = []

        self.step = 0

        self.all_object = set()
        self.near_aster = []
        self.target_move_to = None
        self.common_payload = None

        self.list_of = []

        self.health_limit = 0.5

    def on_born(self):
        self.start_time = datetime.datetime.now()
        self.my_team.append(self)
        self.common_payload = sum([ast.payload for ast in self.asteroids])

        self.max_id = len(self.scene.drones)
        near_aster = sorted(self.asteroids, key=lambda asteroid: self.distance_to(asteroid))
        near_aster = near_aster[:7]
        if len(near_aster) >= self.max_id:
            self.move_to(near_aster[self.my_team.index(self)])
            return self.next_action()
        else:
            self.move_to(choice(near_aster))

    def next_action(self):
        while not self.operation:
            self.update_all_data()
            if self.my_asteroids and self._sleep_countdown > 9:
                self.operation = (self.collect_elerium, False)
            elif self.meter_2
            else:
                self.operation = (self.go_home, False)
            break
        if not self.operation:
            self.operation = (self.go_home, False)
            return
        elif self.operation[1]:
            arg = self.operation[1]
            self.operation[0](arg)
            self.operation = ()
        else:
            self.operation[0]()
            self.operation = ()

    def update_all_data(self):
        self.near_aster = sorted(self.all_object, key=lambda asteroid: self.distance_to(asteroid))
        self.near_aster = self.near_aster[:3]
        self.my_asteroids = [asteroid for asteroid in self.asteroids if asteroid.payload > 0]

    def move_to(self, destination):
        self.target_move_to = destination

        if self.is_empty:
            self.distance_flown_empty += self.distance_to(self.target_move_to)
        elif self.free_space > 0:
            self.distance_flown_partially_loaded += self.distance_to(self.target_move_to)
        elif self.is_full:
            self.distance_flown_full += self.distance_to(self.target_move_to)

        super().move_at(self.target_move_to)

    def go_home(self):
        self.update_all_data()
        self.operation = (self.move_to, self.my_mothership)
        if self.distance_to(self.my_mothership) < 20:
            self.unload_to(self.my_mothership)
        self.next_action()

    def sorted_by_near(self):
        self.update_all_data()
        return sorted(self.my_asteroids, key=lambda asteroid: self.distance_to(asteroid))

    def sorted_by_elerium(self):
        self.update_all_data()
        return sorted(self.my_asteroids, key=lambda asteroid: asteroid.payload, reverse=True)

    def sorted_by_elerium_near(self):
        self.update_all_data()
        asteroid_elerium = sorted(self.my_asteroids, key=lambda asteroid: asteroid.payload, reverse=True)
        asteroid_elerium_near = [asteroid for asteroid in asteroid_elerium if self.distance_to(asteroid) <= 350]
        return sorted(asteroid_elerium_near, key=lambda asteroid: asteroid.payload, reverse=True)

    def get_asteroid(self, sorted_func, random=False):
        elerium_quantity = [asteroid for asteroid in self.my_asteroids if
                            asteroid.payload >= 100 and self.distance_to(asteroid) <= 450]
        sorted_asteroid = sorted_func()
        if random:
            if len(sorted_asteroid) >= 3:
                sorted_asteroid = sorted_asteroid[:3]
                return choice(sorted_asteroid)
        if elerium_quantity:
            return elerium_quantity[0]
        for asteroid in sorted_asteroid:
            return asteroid

    @property
    def asteroid_assigned_to_you(self):
        return self.get_asteroid(sorted_func=self.sorted_by_elerium_near) if self.step < 2 else \
            self.get_asteroid(sorted_func=self.sorted_by_near)

    def collect_elerium(self):
        self.update_all_data()
        for asteroid in self.my_asteroids:
            if self.distance_to(asteroid) < 20:
                self.operation = (self.load_from, asteroid)
                return self.next_action()
        if self.is_full:
            self.operation = (self.go_home, False)
            return self.next_action()

        self.destination = self.get_asteroid(sorted_func=self.sorted_by_near, random=True)
        if self.check_destination(check=True):
            return self.next_action()

        self.destination = self.get_asteroid(sorted_func=self.sorted_by_elerium_near)
        if self.check_destination(check=True):
            return self.next_action()

        self.destination = self.get_asteroid(sorted_func=self.sorted_by_near, random=True)
        if self.check_destination(check=False):
            return self.next_action()

        self.operation = (self.go_home, False)
        self.next_action()

    def check_destination(self, check=False):
        if self.destination and self.free_space < 20 and self.distance_to(self.destination) > 500:
            self.operation = (self.go_home, False)
            return True
        if self.destination and check:
            if self.check_who_already_go(self.destination):
                self.operation = (self.move_to, self.destination)
                return True
            return False
        if self.destination:
            self.operation = (self.move_to, self.destination)
            return True
        return False

    def check_who_already_go(self, destination):
        who_at_destination = [drone for drone in self.scene.drones if drone.target == destination]
        if len(who_at_destination) == 1:
            return True if who_at_destination[0].target.payload > who_at_destination[0].free_space else False
        elif len(who_at_destination) > 1:
            return False
        return True

    def on_stop_at_mothership(self, mothership):
        self.step += 1
        if self.my_asteroids:
            self.turn_to(self.my_asteroids[0])
        return self.next_action()

    def on_stop_at_asteroid(self, asteroid):
        self.update_all_data()
        if asteroid.payload > 0 and self.free_space > 0:
            self.operation = (self.load_from, asteroid)
            return self.next_action()
        if self.is_full:
            self.turn_to(self.my_mothership)
            self.operation = (self.go_home, False)
            return self.next_action()
        return self.next_action()

    def on_load_complete(self):
        self.update_all_data()
        if self.free_space > 0 and self.my_asteroids:
            self.operation = (self.collect_elerium, False)
        elif self.is_full:
            self.operation = (self.go_home, False)
        else:
            if self.near_aster:
                self.operation = (self.move_to, choice(self.near_aster))
        return self.next_action()

    def on_unload_complete(self):
        self.update_all_data()
        if self.is_empty:
            if self.check_the_payload():
                print(f'Пролетели расстояние пустыми: {round(self.distance_flown_empty)}')
                print(f'Пролетели расстояние частично загруженными: {round(self.distance_flown_partially_loaded)}')
                print(f'Пролетели расстояние полностью загруженными: {round(self.distance_flown_full)}')
                self.time_elapsed = datetime.datetime.now() - self.start_time
                print(f'Затраченное время: {self.time_elapsed}')

        self.next_action()

    def check_the_payload(self):
        return self.my_mothership.payload == self.common_payload

    def on_wake_up(self):
        if not self.near_aster:
            self.operation = (self.move_to, self.my_mothership)
        else:
            self.turn_to(choice(self.near_aster))
            self.operation = (self.move_to, choice(self.near_aster))
            self.next_action()

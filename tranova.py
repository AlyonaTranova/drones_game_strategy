rom random import uniform, shuffle
import math
from astrobox.core import Drone, Asteroid
from astrobox.themes.default import MOTHERSHIP_HEALING_DISTANCE
from robogame_engine import GameObject
from robogame_engine.geometry import Point, Vector
from robogame_engine.theme import theme


class Administration:
    roles = {}
    asteroids_for_base = []

    def __init__(self):
        self.comrades = []
        self.asteroids_in_work = []
        self.enemies = []

        self.path_is_fully_loaded = 0
        self.path_half_loaded = 0
        self.path_is_empty = 0

    def new_comrade(self, comrade):
        number_drones = len(self.comrades)
        self.get_roles(number_drones + 1, comrade.have_gun)
        self.add_comrade(comrade)
        for index, comrade in enumerate(self.comrades):
            self.give_role(comrade, index)

    def give_role(self, comrade, index):
        all_roles = [Spying for _ in range(self.roles["spying"])]
        all_roles.extend([Transporting for _ in range(self.roles["transporting"])])
        all_roles.extend([Fighting for _ in range(self.roles["fighting"])])
        all_roles.extend([Collecting for _ in range(self.roles["collecting"])])
        all_roles.extend([BaseGuarding for _ in range(self.roles["base guarding"])])
        all_roles.extend([Turret for _ in range(self.roles["turret"])])
        this_role = all_roles[index]
        comrade.role = this_role(unit=comrade)

    def get_roles(self, number_drones, have_gun):
        if have_gun:
            transports = 0
            collectors = 5
            combats = 0
            spy = 0
            turret = 0
            guard = max(0, number_drones - collectors - spy - turret - transports - combats)
            Administration.roles["collecting"] = collectors
            Administration.roles["transporting"] = transports
            Administration.roles["spying"] = spy
            Administration.roles["fighting"] = combats
            Administration.roles["base guarding"] = guard
            Administration.roles["turret"] = turret
        else:
            collectors = number_drones
            Administration.roles["collecting"] = collectors
            Administration.roles["transporting"] = 0
            Administration.roles["spying"] = 0
            Administration.roles["fighting"] = 0
            Administration.roles["base guarding"] = 0
            Administration.roles["turret"] = 0

    def add_comrade(self, comrade):
        comrade.administration = self
        comrade.operations = []
        comrade.base = None
        comrade.old_asteroid = None
        self.comrades.append(comrade)

    def get_operations(self, comrade):

        enemies = self.get_enemies(comrade)
        if len([1 for s in self.comrades if s.is_alive]) <= 2 \
                and not isinstance(comrade.role, Turret) \
                and len(enemies) > 0 \
                and comrade.have_gun:
            comrade.role.change_role(Turret)
            comrade.operations.append(['move', comrade.my_mothership, 1])
            return

        if (isinstance(comrade.role, Collecting) and not isinstance(comrade.role, Transporting)
                and comrade.have_gun and comrade.my_mothership.payload > 1000):
            enemies = self.get_enemies_by_base(comrade.my_mothership)
            for enemy in enemies:
                if not (enemy in self.enemies):
                    comrade.role.change_role(Defending)
                    comrade.role.next_step(enemy)
                    self.enemies = [enemy]
                    break

        if comrade.meter_2 < comrade.limit_health:
            comrade.operations.append(['move', comrade.my_mothership, 1])
            return

        purpose = comrade.role.next_purpose()
        if isinstance(comrade.role, BaseGuarding):
            enemies = self.get_enemies_by_base(comrade.my_mothership, nearest=False)
            if enemies:
                purpose = enemies[0]
            else:
                purpose = None

        if purpose:
            comrade.role.next_step(purpose)
        else:
            comrade.role.change_role()

    def get_enemies_by_base(self, base, nearest=True):
        enemies = self.get_enemies(base)
        result = []
        for enemy in enemies:
            if enemy[1] < MOTHERSHIP_HEALING_DISTANCE * 2 or not nearest:
                result.append(enemy[0])
        return result

    def get_enemies(self, comrades):
        enemies = [(drone, comrades.distance_to(drone)) for drone in comrades.scene.drones if
                   comrades.team != drone.team and drone.is_alive]
        enemies.sort(key=lambda x: x[1])
        return enemies

    def get_enemies_with_guns(self, comrades):
        enemies = [(drone, comrades.distance_to(drone)) for drone in comrades.scene.drones if
                   comrades.team != drone.team and drone.is_alive and drone.have_gun]
        enemies.sort(key=lambda x: x[1])
        return enemies

    def nearest_enemy_mothership(self, comrades):
        motherships = [m for m in comrades.scene.motherships if m.team != comrades.unit.team and m.is_alive]
        if motherships:
            motherships = sorted(motherships, key=lambda x: x.distance_to(comrades.unit))
            return motherships[0]
        return None

    def non_functional_enemy_mothership(self, comrades):
        enemy_motherships = [mothership for mothership in comrades.scene.motherships if
                             not mothership.is_alive and not mothership.is_empty]
        return enemy_motherships

    def remove_item_asteroids_in_work(self, item):
        if item in self.asteroids_in_work:
            index = self.asteroids_in_work.index(item)
            self.asteroids_in_work.pop(index)

    def get_place_for_attack(self, comrade, target):
        if isinstance(target, GameObject):
            vector = Vector.from_points(target.coord, comrade.coord)
        elif isinstance(target, Point):
            vector = Vector.from_points(target, comrade.coord)
        else:
            raise Exception("target must be GameObject or Point!".format(target, ))

        distance = vector.module
        _coef = 1 / distance
        norm_vector = Vector(vector.x * _coef, vector.y * _coef)
        vector_gunshot = norm_vector * min(int(comrade.attack_range), int(distance))
        purpose = Point(target.coord.x + vector_gunshot.x, target.coord.y + vector_gunshot.y)
        angles = [0, 60, -60, 30, -30]
        shuffle(angles)
        for angle in angles:
            place = self.get_place_near(purpose, target, angle)
            if place and comrade.check_place_for_attack(place):
                return place
        return None

    def get_place_near(self, point, target, angle):
        vec = Vector(point.x - target.x, point.y - target.y)
        vec.rotate(angle)
        return Point(target.x + vec.x, target.y + vec.y)

    def get_place_near_mothership(self, comrade):
        center_field = Point(theme.FIELD_WIDTH // 2, theme.FIELD_HEIGHT // 2)
        vector = Vector.from_points(comrade.my_mothership.coord, center_field)
        distance = vector.module
        _coef = 1 / distance
        norm_vector = Vector(vector.x * _coef, vector.y * _coef)
        vector_position = norm_vector * MOTHERSHIP_HEALING_DISTANCE * 0.9
        position = Point(comrade.my_mothership.coord.x + vector_position.x,
                         comrade.my_mothership.coord.y + vector_position.y)
        return position

    def game_over(self):
        print('Было пройдено полностью загруженным :',
              round(sum([getattr(member, 'path_is_fully_loaded') for member in self.comrades])))
        print('Было пройдено пустым :',
              round(sum([getattr(member, 'path_is_empty') for member in self.comrades])))
        print('Было пройдено частично загруженным :',
              round(sum([getattr(member, 'path_half_loaded') for member in self.comrades])))


class TranovaDrone(Drone):
    operations = []
    administration = None
    attack_range = 0
    limit_health = 0.5
    cost_forpost = 0
    role = None

    def registration(self):
        if TranovaDrone.administration is None:
            TranovaDrone.administration = Administration()
        TranovaDrone.administration.new_comrade(self)

    def born_comrade(self):
        self.registration()
        if self.have_gun:
            self.attack_range = self.gun.shot_distance
        self.limit_health = uniform(0.3, 0.5)

        if isinstance(self.role, Transporting):
            candidats_asteroids_for_base = min([(asteroid.distance_to(self.my_mothership), asteroid)
                                                for asteroid in self.asteroids if
                                                asteroid not in self.asteroids_for_base])

            candidat_base = candidats_asteroids_for_base[1]
            self.add_base(candidat_base)
            self.base = candidat_base
        else:
            self.base = self.my_mothership

    def next_operation(self):
        i = 0
        while not self.operations:
            self.administration.get_operations(self)
            i += 1
            if i > 5:
                return

        operation, target, is_performed = self.operations[0]
        if operation == "move":
            if is_performed:
                self.operations[0][2] = 0
                self.move_to(target)
            else:
                self.operations.pop(0)
                self.next_operation()

        elif operation == "unload":
            self.operations.pop(0)
            self.unload_to(target)

        elif operation == "load":
            self.operations.pop(0)
            self.load_from(target)

        elif operation == "it is free":
            self.operations.pop(0)
            self.asteroid_is_free(target)
            self.next_operation()

        elif operation == "turn":
            self.operations.pop(0)
            self.turn_to(target)

        elif operation == "shoot":
            self.operations.pop(0)
            self.shoot(target)
            self.next_operation()

        elif operation == "move to":
            if is_performed == 1:
                self.operations[0][2] = 2
                self.move_to_step(target)
            else:
                self.operations.pop(0)
                self.next_operation()

        elif operation == "pass":
            self.operations.pop(0)
            self.move_to_step(self.coord)

        else:
            self.operations.pop(0)
            self.next_operation()

        if isinstance(target, Asteroid):
            self.old_asteroid = target

    def move_to(self, target):
        self.cost_forpost = 0

        length = self.distance_to(target)
        if self.is_empty:
            self.administration.path_is_empty += length
        elif self.free_space > 0:
            self.administration.path_half_loaded += length
        elif self.is_full:
            self.administration.path_is_fully_loaded += length

        super().move_at(target)

    def move_to_step(self, target):
        distance = min(250, max(100, self.distance_to(target) - 50))
        vec = Vector.from_direction(self.direction, distance)
        new_coord = Point(x=self.coord.x + vec.x, y=self.coord.y + vec.y)
        self.move_to(new_coord)

    def sorted_by_near(self):
        return sorted(self.administration.asteroids_in_work, key=lambda asteroid: self.distance_to(asteroid))

    def sorted_by_rich(self):
        return sorted(self.administration.asteroids_in_work, key=lambda asteroid: asteroid.payload, reverse=True)

    def sorted_by_rich_near(self):
        asteroid_rich = sorted(self.administration.asteroids_in_work, key=lambda asteroid: asteroid.payload,
                               reverse=True)
        aster_rich_near = [aster for aster in asteroid_rich if self.distance_to(aster) <= 400]
        return sorted(aster_rich_near, key=lambda asteroid: asteroid.payload, reverse=True)

    def shoot(self, target):
        if not self.have_gun:
            self.role.change_role(Collecting)
            return

        if self.distance_to(self.my_mothership) < 150:
            self.operations.append(["pass", self, 1])
            return

        for comrade in self.administration.comrades:
            if not comrade.is_alive or comrade is self:
                continue
            if isinstance(target, GameObject) and self.distance_to(target) > comrade.distance_to(target) \
                    and self.get_angle(comrade, target) < 20 \
                    and self.distance_to(comrade) < self.distance_to(target) \
                    and comrade.distance_to(target) > 10 \
                    and not isinstance(self.role, Turret):
                point_attack = self.administration.get_place_for_attack(self, target)
                if point_attack and self.cost_forpost < 10:
                    self.operations.append(['move', point_attack, 1])
                return

        if not self.check_place_for_attack(self.coord):
            point_attack = self.administration.get_place_for_attack(self, target)
            if point_attack and self.cost_forpost < 10:
                self.operations.append(['move', point_attack, 1])

        if self.gun_cooldown:
            self.operations.append(['turn', target, 1])

        self.cost_forpost += 1
        self.gun.shot(target)

    def check_place_for_attack(self, point: Point):
        place_is_valid = 0 < point.x < theme.FIELD_WIDTH and 0 < point.y < theme.FIELD_HEIGHT
        for comrade in self.administration.comrades:
            if not comrade.is_alive or comrade is self:
                continue
            place_is_valid = place_is_valid and (comrade.distance_to(point) >= 50)
        return place_is_valid

    def check_enemies_in_sight(self, comrades):
        if self.have_gun:
            living_enemies = self.administration.get_enemies(comrades)
            if living_enemies:
                for enemy, dist in living_enemies:
                    if enemy.my_mothership.is_alive:
                        enemy_coord = enemy.distance_to(enemy.my_mothership)
                        if enemy_coord > 200:
                            return enemy
                    else:
                        return enemy

    def get_angle(self, partner: GameObject, target: GameObject):
        v12 = Vector(self.coord.x - target.coord.x, self.coord.y - target.coord.y)
        v32 = Vector(partner.coord.x - target.coord.x, partner.coord.y - target.coord.y)
        res = v12.x * v32.x + v12.y * v32.y
        _cos = res / (v12.module * v32.module + 1.e-8)
        return math.degrees(math.acos(_cos))

    def add_base(self, base):
        self.administration.asteroids_for_base.append(base)

    def asteroid_is_free(self, asteroid):
        self.administration.remove_item_asteroids_in_work(asteroid)

    @property
    def asteroids_for_base(self):
        if hasattr(self.administration, "asteroids_for_base"):
            return self.administration.asteroids_for_base
        else:
            return self.my_mothership

    def on_born(self):
        self.born_comrade()
        near_asteroid = [(self.distance_to(aster), aster) for aster in self.asteroids]
        near_asteroid.sort(key=lambda x: x[0])
        idx = len(self.administration.comrades) - 1
        if self.have_gun:
            point_attack = self.administration.get_place_for_attack(self, near_asteroid[idx][1])
            if point_attack:
                self.operations.append(['move to', point_attack, 1])
        else:
            self.operations.append(["move to", near_asteroid[idx][1], 1])

        self.next_operation()

    def on_stop_at_asteroid(self, asteroid):
        self.next_operation()

    def on_load_complete(self):
        self.next_operation()

    def on_stop_at_mothership(self, mothership):
        self.next_operation()

    def on_unload_complete(self):
        self.next_operation()

    def on_stop_at_point(self, target):
        self.next_operation()

    def on_stop(self):
        self.next_operation()

    def on_wake_up(self):
        self.operations = [["pass", self, 1]]
        self.next_operation()


class Attitude:

    def __init__(self, unit: TranovaDrone):
        self.unit = unit

    def change_role(self, role=None):
        comrade = self.unit
        if not role:
            comrade.role = comrade.role.next()
        else:
            comrade.role = role(comrade)

    def next(self):
        return Collecting(self.unit)


class Collecting(Attitude):

    def next_purpose(self):
        if self.unit.is_full:
            return self.unit.base

        administration = self.unit.administration
        forbidden_asteroids = list(administration.asteroids_in_work)
        if isinstance(self, Transporting):
            asteroids = self.unit.administration.sorted_by_rich_near()
            # asteroids = [asteroid for asteroid in self.unit.scene.asteroids if asteroid not in forbidden_asteroids]
            free_elerium = sum([asteroid.payload for asteroid in asteroids])
            if free_elerium < 2000:
                administration.asteroids_for_base = []
                self.unit.base = self.unit.my_mothership
                return None
            else:
                forbidden_asteroids += administration.asteroids_for_base

        if not hasattr(self.unit.scene, "asteroids"):
            return None

        asteroids = [asteroid for asteroid in self.unit.scene.asteroids if asteroid not in forbidden_asteroids]
        enemy_motherships = [mothership for mothership in self.unit.scene.motherships if
                             not mothership.is_alive and not mothership.is_empty]
        asteroids.extend(enemy_motherships)
        asteroids.extend([drone for drone in self.unit.scene.drones
                          if not drone.is_alive and not drone.is_empty])

        first_purpose = self.find_nearest_purpose(asteroids=asteroids, threshold=self.unit.free_space)
        if first_purpose:
            return first_purpose

        purposes = [(asteroid.payload, asteroid) for asteroid in asteroids if asteroid.payload > 0]
        if purposes:
            second_purpose = max(purposes, key=lambda x: x[0])
            return second_purpose[1]
        return None

    def find_nearest_purpose(self, asteroids, threshold=1):
        comrade = self.unit
        purposes = [(comrade.distance_to(asteroid) + asteroid.distance_to(comrade.base), asteroid)
                    for asteroid in asteroids if
                    asteroid.payload >= threshold]

        if purposes:
            if isinstance(self, Transporting):
                purpose = max(purposes, key=lambda x: x[0])[1]
            else:
                purpose = min(purposes, key=lambda x: x[0])[1]
        else:
            purpose = None

        if purpose == comrade.old_asteroid:
            purpose = None

        return purpose

    def next_step(self, purpose):
        comrade = self.unit
        comrade.operations.append(['move', purpose, 1])
        if purpose == comrade.base:
            if not comrade.is_empty:
                comrade.operations.append(['unload', purpose, 1])
            else:
                if comrade.my_mothership.payload > 1000:
                    comrade.role.change_role()
                return
        elif not comrade.is_full:
            comrade.administration.asteroids_in_work.append(purpose)
            comrade.operations.append(['load', purpose, 1])
        else:
            comrade.operations.append(['unload', comrade.my_mothership, 1])
        comrade.operations.append(['it is free', purpose, 1])

        if purpose == comrade.old_asteroid:
            comrade.next_operation()
            if comrade.my_mothership.payload > 1000:
                self.change_role()

    def next(self):
        if self.unit.have_gun:
            return Fighting(self.unit)
        return BackToBase(self.unit)


class Transporting(Collecting):
    def next(self):
        if self.unit.have_gun and self.unit.my_mothership.payload > 950:
            return Spying(self.unit)
        return Collecting(self.unit)


class BackToBase(Attitude):
    def next_purpose(self):
        return self.unit.my_mothership

    def next_step(self):
        comrade = self.unit
        if comrade.distance_to(comrade.my_mothership) > 10:
            comrade.operations = [['move', comrade.my_mothership, 1]]

        if not comrade.is_empty:
            comrade.operations.append(['unload', self.unit.my_mothership, 1])

    def next(self):
        return self


class Defending(Attitude):

    def __init__(self, unit: TranovaDrone):
        super().__init__(unit)
        self.enemy = None
        self.unit.operations = []

    def next_purpose(self):

        if self.enemy is not None and self.enemy.is_alive and self.enemy.distance_to(self.enemy.mothership) \
                and self.enemy.cargo.payload > 0:
            distance_victim = self.enemy.distance_to(self.enemy.my_mothership)
            if distance_victim > theme.MOTHERSHIP_SAFE_DISTANCE:
                return self.enemy
        self.enemy = None
        return None

    def next_step(self, target):
        comrade = self.unit
        self.enemy = target
        self.enemy = comrade.check_enemies_in_sight(comrade)
        if comrade.distance_to(target) > comrade.attack_range:
            point_attack = comrade.administration.get_place_for_attack(comrade, target)
            if point_attack:
                comrade.operations.append(['move to', point_attack, 1])

        comrade.operations.append(['turn', target, 1])
        comrade.operations.append(['shoot', target, 1])

    def next(self):
        return Collecting(self.unit)


class Fighting(Defending):

    def next_purpose(self):
        self.enemy = super().next_purpose()
        if self.enemy and self.enemy.distance_to(self.enemy.my_mothership) > MOTHERSHIP_HEALING_DISTANCE:
            return self.enemy

        comrade = self.unit
        enemies = comrade.administration.get_enemies(comrade)
        print(enemies)
        if enemies:
            self.enemy = enemies[0][0]
            return self.enemy

        self.enemy = None
        return None

    def next(self):
        if not self.enemy:
            return Collecting(self.unit)
        return Spying(self.unit)


class Spying(Defending):

    def next_purpose(self):
        if self.victim and self.victim.is_alive:
            return self.victim

        comrade = self.unit
        enemy_bases = comrade.administration.nearest_enemy_mothership(comrade)
        if enemy_bases:
            self.victim = enemy_bases[0][0]
            return self.victim
        self.victim = None
        return None

    def next_step(self, target):
        comrade = self.unit
        self.victim = target

        if comrade.distance_to(target) > comrade.attack_range:
            point_attack = comrade.administration.get_place_for_attack(comrade, target)
            if point_attack:
                comrade.operations.append(['move to', point_attack, 1])

        comrade.operations.append(['turn', target, 1])
        comrade.operations.append(['shoot', target, 1])

    def next(self):
        comrade = self.unit
        enemies = comrade.administration.get_enemies(comrade)
        dead_motherships = comrade.administration.non_functional_enemy_mothership(comrade)
        if enemies:
            print('3')
            return Fighting(self.unit)
        if dead_motherships:
            print('4')
            return Collecting(self.unit)
        return Fighting(self.unit)


class BaseGuarding(Defending):

    def next_purpose(self):
        if self.victim and self.victim.is_alive and self.victim.distance_to(
                self.victim.my_mothership) > MOTHERSHIP_HEALING_DISTANCE:
            return self.victim
        return None

    def next_step(self, target):
        comrade = self.unit
        self.victim = target
        if comrade.distance_to(target) > comrade.attack_range:
            point_attack = comrade.administration.get_place_for_attack(comrade, target)
            if point_attack:
                comrade.operations.append(['move to', point_attack, 1])
        comrade.operations.append(['turn', target, 1])
        comrade.operations.append(['shoot', target, 1])

    def next(self):
        comrade = self.unit
        enemies = comrade.administration.get_enemies(comrade)
        if len(enemies) == 0:
            return Collecting(self.unit)
        return Spying(self.unit)


class Turret(Defending):

    def next_purpose(self):
        comrade = self.unit
        enemies = comrade.administration.get_enemies(comrade)
        if enemies:
            return enemies[0][0]

        return None

    def next_step(self, target):
        comrade = self.unit

        if target:
            comrade.operations.append(['turn', target, 1])
            comrade.operations.append(['shoot', target, 1])
        elif comrade.distance_to(comrade.my_mothership) > MOTHERSHIP_HEALING_DISTANCE * 0.95:
            point_attack = comrade.administration.get_place_near_mothership(comrade)
            comrade.operations.append(['move', point_attack, 1])

    def next(self):
        return Collecting(self.unit)

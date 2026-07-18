# CETrain.py
"""
Pure data representation of the trains: cars, loot, and topology.
No rules logic lives here (see engine/CERules.py for legality checks) -
these classes just hold state and asnwer simple structural questions.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional
import random

class LootType(Enum):
    PURSE = auto()
    JEWEL = auto()
    STRONGBOX = auto()

PURSE_VALUES = [250, 300, 350, 400, 450]
JEWEL_VALUE = 500
STRONGBOX_VALUE = 1000  # only ever in the Locomotive at setup
# The full purse population used by Train.build_base_game(). Pulled out to a
# module constant (rather than left inline) so belief_state.py can compute a
# card-counting-style average loot value from the same numbers instead of
# duplicating them.
PURSE_POOL = ([250] * 12) + ([300] * 2) + [350, 400, 450, 500]
BASE_PASSENGER_LOOT_POOLS = [
    [3, 0],
    [4, 1],
    [3, 1],
    [1, 0],
    [1, 1],
    [0, 3]
]

@dataclass(frozen=True)
class Loot:
    kind: LootType
    value: int

    def __repr__(self):
        return f"({self.kind.name}: {self.value})"


@dataclass
class TrainCar:
    id: int
    is_locomotive: bool = False
    loot_inside: List[Loot] = field(default_factory=list)
    loot_roof: List[Loot] = field(default_factory=list)

    def loot_at(self, on_roof: bool) -> List[Loot]:
        return self.loot_roof if on_roof else self.loot_inside

    def remove_loot(self, loot: Loot, on_roof: bool) -> bool:
        pool = self.loot_at(on_roof)
        if loot in pool:
            pool.remove(loot)
            return True
        return False
    
    def add_loot(self, loot: Loot, on_roof: bool) -> None:
        self.loot_at(on_roof).append(loot)


@dataclass
class Train:
    cars: List[TrainCar]

    def get_car(self, car_id: int) -> Optional[TrainCar]:
        """Safely retrieve a car; returns None if ID is invalid."""
        if 0 <= car_id < len(self.cars):
            return self.cars[car_id]
        return None
    
    def neighbors(self, car_id: int) -> List[int]:
        """Adjacent car ids (for MOVE / adjacency-based SHOOT/PUNCH checks)."""
        result = []
        if car_id - 1 >= 0:
            result.append(car_id - 1)
        if car_id + 1 < len(self.cars):
            result.append(car_id + 1)
        return result
    
    def roof_line_of_sight(self, car_id: int, direction: int) -> List[int]:
        """
        Cars visible from car_id's roof looking in one direction (+1 toward
        caboos, -1 toward locomotive) - a bandit on the roof can shoot
        anyone on a roof in that line, not just the adjacent car.
        Blocking by bandits standing in the line is filtered in
        engine/CERules.py.
        """
        result = []
        step = 1 if direction >= 0 else -1
        cid = car_id + step
        while 0 <= cid < len(self.cars):
            result.append(cid)
            cid += step
        return result
    
    @property
    def locomotive_id(self) -> int:
        for car in self.cars:
            if car.is_locomotive:
                return car.id
        return 0
    
    # ---- setup ----
    @classmethod
    def build_base_game(cls, num_players: int, seed: Optional[int] = None) -> "Train":
        """
        Builds a Locomotive + num_players cars with randomized loot.
        """
        rng = random.Random(seed)

        # 1. Prepare global loot pool
        purses = ([250] * 12) + ([300] * 2) + [350, 400, 450, 500]
        # Remove starting parses for players
        for _ in range(num_players):
            purses.pop(0)

        rng.shuffle(purses)

        # 2. Build the Locomotive
        cars = []
        loco = TrainCar(id=0, is_locomotive=True)
        loco.add_loot(Loot(LootType.STRONGBOX, 1000), on_roof=False)
        cars.append(loco)

        # 3. Build exactly 'num_players' cars
        if num_players > len(BASE_PASSENGER_LOOT_POOLS):
            raise ValueError("Not enough unique loot pool configurations for the number of players.")

        selected_configs = rng.sample(BASE_PASSENGER_LOOT_POOLS, num_players)

        for i, (num_purses, num_jewels) in enumerate(selected_configs, start=1):
            car = TrainCar(id=i)

            # Add purses
            for _ in range(num_purses):
                if purses:
                    val = purses.pop()
                    car.add_loot(Loot(LootType.PURSE, val), on_roof=False)

            # Add jewels
            for _ in range(num_jewels):
                car.add_loot(Loot(LootType.JEWEL, JEWEL_VALUE), on_roof=False)
            cars.append(car)

        return cls(cars=cars)











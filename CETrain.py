# CETrain.py

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional
import random

# Enums to represent car and loot types
class CarType(Enum):
    LOCOMOTIVE = auto()
    PASSENGER = auto()
    CABOOSE = auto()

class LootType(Enum):
    PURSE = auto()
    STRONGBOX = auto()
    JEWEL = auto()

# Loot class
@dataclass(frozen=True)
class Loot:
    kind: LootType
    value: int

    def __repr__(self):
        return f"({self.kind.name}, {self.value})"

PURSE_VALUES = [250, 300, 350, 400, 450]

# Randomly creates a purse loot item
def draw_purse(rng: random.Random) -> Loot:
    return Loot(
        kind=LootType.PURSE,
        value=rng.choice(PURSE_VALUES),
    )

# Generates the full list of loot items for a given train's stats
def generate_car_loot(rng: random.Random, purses: int = 0, jewels: int = 0, strongboxes: int=0) -> list[Loot]:
    # Add randomized purses, jewels, and strongboxes for count
    loot = [draw_purse(rng) for _ in range(purses)]
    loot += [Loot(LootType.JEWEL, 500) for _ in range(jewels)]
    loot += [Loot(LootType.STRONGBOX, 1000) for _ in range(strongboxes)] 
    return loot

@dataclass
class TrainCar(object):
    car_type: CarType

    loot_inside: List[Loot] = field(default_factory=list)
    loot_roof: List[Loot] = field(default_factory=list)

    bandits_inside: List[str] = field(default_factory=list)
    bandits_roof: List[str] = field(default_factory=list)
    
    has_marhsal: bool = False

    def __repr__(self):
        return f"Car({self.car_type.name}, Inside: {self.loot_inside})"

class Train(object):
    def __init__(self, cars: List[TrainCar]):
        self.cars = cars

    def __repr__(self):
        car_strings = "\n ".join([repr(car) for car in self.cars])
        return f"Train with {len(self.cars)} cars: \n {car_strings}"

BASE_GAME_PASSENGER_TRAINS = [
    [3],
    [4,1],
    [3,1],
    [1],
    [1,1],
    [0,3]
]

def generate_train(
    num_players: int,
    seed: Optional[int] = None
) -> Train:
    """
    Creates a Train by generating the appropriate number of
    passanger trains and populating them with randomized loot
    """
    if not (2 <= num_players <= 6):
        raise ValueError(f"Number of players not within playable range (2,6), inputted player count={num_players}")
    
    rng = random.Random(seed)
    passenger_cars = rng.choices(BASE_GAME_PASSENGER_TRAINS, k=num_players)
    
    cars = []
    for idx, pt in enumerate(passenger_cars):
        ct = CarType.CABOOSE if idx == 0 else CarType.PASSENGER
        cars.append(TrainCar(ct, generate_car_loot(rng, *pt)))
    
    cars.append(TrainCar(CarType.LOCOMOTIVE, generate_car_loot(rng, *[0, 0, 1])))
    
    return Train(cars)

print(generate_train(3))
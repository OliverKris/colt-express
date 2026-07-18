# CEPieces.py
"""
Bandit and Marshal pieces. Like CETrain.py, these hold state and expose
small state-mutating helpers (move/climb) but never decide legality -
that's engine/CERules.py's job.
"""

from dataclasses import dataclass, field
from typing import List
from models.CETrain import Loot

@dataclass
class BanditType:
    name: str
    color: str
    ability: str = ""  # TODO: base-game character powers

BASE_BANDITS = {
    "GHOST": BanditType(name="Ghost", color="White"),
    "DOC": BanditType(name="Doc", color="Blue"),
    "TUCO": BanditType(name="Tuco", color="Red"),
    "CHEYENNE": BanditType(name="Cheyenne", color="Green"),
    "BELLE": BanditType(name="Belle", color="Pink"),
    "DJANGO": BanditType(name="Django", color="Black"),
}


@dataclass
class Bandit:
    """Represents a single player/AI piece."""
    name: str
    bandit_type: BanditType
    current_car_id: int
    is_on_roof: bool = False
    loot: List[Loot] = field(default_factory=list)
    bullets_remaining: int = 6  # shots left before this bandit is out of ammo

    def is_at(self, car_id: int, on_roof: bool) -> bool:
        return self.current_car_id == car_id and self.is_on_roof == on_roof

    def total_loot_value(self) -> int:
        return sum(item.value for item in self.loot)

    def move(self, new_car_id: int) -> None:
        self.current_car_id = new_car_id

    def climb(self) -> None:
        self.is_on_roof = not self.is_on_roof

    def add_loot(self, item: Loot) -> None:
        self.loot.append(item)

    def drop_loot(self, index: int) -> Loot:
        """Removes and returns one loot items at the given index."""
        if not (0 <= index < len(self.loot)):
            raise ValueError(f"Invalid loot index: {index}. Bandit has {len(self.loot)} items.")
        return self.loot.pop(index)


@dataclass
class Marshal:
    current_car_id: int = 0  # starts in the Locomotive

    def move(self, new_car_id: int):
        self.current_car_id = new_car_id
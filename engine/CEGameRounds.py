# CEGameRounds.py

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto
import random

class TurnType(Enum):
    NORMAL = auto()
    TUNNEL = auto() # Players play actions face-down
    SPEED = auto() # Players take 2 turns in a row
    SWITCH = auto() # Players take their turns in counter-clockwise order

BASE_ROUNDS = {
    "2-4": [ 
        # Round defaults for player count 2-4
        [TurnType.NORMAL, TurnType.TUNNEL, TurnType.NORMAL, TurnType.NORMAL], # Swivel Arm
        [TurnType.NORMAL, TurnType.NORMAL, TurnType.TUNNEL, TurnType.NORMAL, TurnType.NORMAL], # Passangers' Rebellion
        [TurnType.NORMAL, TurnType.NORMAL, TurnType.NORMAL, TurnType.NORMAL], # Braking
        [TurnType.NORMAL, TurnType.TUNNEL, TurnType.SPEED, TurnType.NORMAL], # Take It All!
        [TurnType.NORMAL, TurnType.NORMAL, TurnType.TUNNEL, TurnType.SWITCH], # Angry Marshal
        [TurnType.NORMAL, TurnType.SPEED, TurnType.NORMAL],
        [TurnType.NORMAL, TurnType.TUNNEL, TurnType.NORMAL, TurnType.TUNNEL, TurnType.NORMAL]
    ],
    "5-6": [ 
        # Round defaults for player count 5-6
        [TurnType.NORMAL, TurnType.TUNNEL, TurnType.NORMAL], # Swivel Arm
        [TurnType.NORMAL, TurnType.TUNNEL, TurnType.NORMAL, TurnType.SWITCH], # Passangers' Rebellion
        [TurnType.NORMAL, TurnType.TUNNEL, TurnType.NORMAL, TurnType.NORMAL], # Braking
        [TurnType.NORMAL, TurnType.SPEED, TurnType.SWITCH], # Take It All!
        [TurnType.NORMAL, TurnType.NORMAL, TurnType.SWITCH], # Angry Marshal
        [TurnType.NORMAL, TurnType.SPEED],
        [TurnType.NORMAL, TurnType.TUNNEL, TurnType.NORMAL, TurnType.TUNNEL]
    ],
    "station": [
        # Station rounds
        [TurnType.NORMAL, TurnType.NORMAL, TurnType.TUNNEL, TurnType.NORMAL], # Marhsal's Revenge
        [TurnType.NORMAL, TurnType.NORMAL, TurnType.TUNNEL, TurnType.NORMAL], # Pickpocketing
        [TurnType.NORMAL, TurnType.NORMAL, TurnType.TUNNEL, TurnType.NORMAL], # Hostage Conductor
    ]
}

"""
The game is divided into multiple Rounds. Each round contains multiple Turns,
each with the possibility to have special turn effects. A Round also has the
possibility of having an end_of_round effect
"""

@dataclass
class Turn:
    turn_num: int
    turn_type: TurnType

    def __repr__(self):
        return f"T{self.turn_num}({self.turn_type.name})"


@dataclass
class Round:
    turn_types: List[TurnType] = field(default_factory=list)
    eor_effect: str = ""
    turns: List[Turn] = field(init=False)

    def __post_init__(self):
        self.turns = [
            Turn(i + 1, t_type) for i, t_type in enumerate(self.turn_types)
        ]

    def __repr__(self):
        return f"Round(Turns: {self.turns})"


@dataclass
class GameRounds:
    rounds: List[Round]

    @classmethod
    def create_for_players(cls, num_players: int, seed: Optional[int] = None):
        """Factory method to build rounds based on player count."""
        rng = random.Random(seed)
        key = "2-4" if 2 <= num_players <= 4 else "5-6"

        selected_rounds = rng.sample(BASE_ROUNDS[key], 4)
        selected_station = rng.sample(BASE_ROUNDS["station"], 1)

        rounds = [Round(turn_types=t_list) for t_list in selected_rounds + selected_station]
        return cls(rounds=rounds)
# CEActions.py
"""
Actions are what an Action Card *means* once it's about to be resolved.
Cards are dumb data (models/CECards.py); Actions carry the extra targeting
info (which car, which bandit) that a player chooses when they play a card.
"""

from dataclasses import dataclass
from enum import Enum, auto

from models.CECards import Card, CardType

class ActionType(Enum):
    MOVE = auto()
    CLIMB = auto()
    SHOOT = auto()
    PUNCH = auto()
    LOOT = auto()
    MARSHAL = auto()

# CardType -> ActionType mapping.
CARD_TYPE_TO_ACTION_TYPE = {
    CardType.MOVE: ActionType.MOVE,
    CardType.CLIMB: ActionType.CLIMB,
    CardType.SHOOT: ActionType.SHOOT,
    CardType.PUNCH: ActionType.PUNCH,
    CardType.LOOT: ActionType.LOOT,
    CardType.MARSHAL: ActionType.MARSHAL,
}


def action_type_for_card(card: Card) -> ActionType:
    return CARD_TYPE_TO_ACTION_TYPE[card.type]


@dataclass
class Action:
    """A fully-specified, about-to-be-resolved action: a card, whose it
    was, what type of action it produces, and any target the player chose
    when they played it (a car to move/shoot toward, a bandit to punch)."""

    bandit_name: str
    card: Card
    type: ActionType
    target_car: int = -1
    target_bandit: str = ""
    direction: int = 0  # +1/-1, used for roof shots and >1-car roof moves

    @classmethod
    def from_card(cls, bandit_name: str, card: Card, target_car: int = -1,
                  target_bandit: str = "", direction: int = 0) -> "Action":
        return cls(
            bandit_name=bandit_name,
            card=card,
            type=action_type_for_card(card),
            target_car=target_car,
            target_bandit=target_bandit,
            direction=direction
        )
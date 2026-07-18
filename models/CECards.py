# CECards.py
"""
Card data + a player's personal deck/hand/discard.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List
import random

class CardType(Enum):
    MOVE = auto()
    CLIMB = auto()
    SHOOT = auto()
    PUNCH = auto()
    LOOT = auto()
    MARSHAL = auto()


# Number of each action card in a bandit's personal 10-card deck.
BASE_DECK_COMPOSITION = {
    CardType.MOVE: 2,
    CardType.CLIMB: 2,
    CardType.SHOOT: 2,
    CardType.PUNCH: 1,
    CardType.LOOT: 2,
    CardType.MARSHAL: 1,
}


@dataclass(frozen=True)
class Card:
    type: CardType

    def __repr__(self):
        return f"[{self.type.name}]"


@dataclass(frozen=True)
class BulletCard:
    """A wound card. Neutral - not owned by any bandit until it's fired
    into someone's discard pile."""

    def __repr__(self):
        return "[BULLET]"


@dataclass
class PlayerCards:
    """All cards belonging to a single bandit: hand, personal deck, and
    discard pile. Bullet cards mixed in count as dead draws."""

    hand: List[Card] = field(default_factory=list)
    deck: List[Card] = field(init=False)
    discard_pile: List[Card] = field(default_factory=list)
    hand_size: int = 6  # TODO: Doc has starting hand of 7

    def __post_init__(self):
        self.deck = [Card(c_type) for c_type, count in BASE_DECK_COMPOSITION.items() for _ in range(count)]
        random.shuffle(self.deck)
        self.draw(self.hand_size)

    def draw(self, num: int = 1) -> None:
        """Draws cards from deck to hand, reshuffling discard if necessary."""
        for _ in range(num):
            if not self.deck:
                if not self.discard_pile:
                    break  # deck and discard both empty - nothing left to draw
                self._reshuffle_discard_into_deck()
            if self.deck:
                self.hand.append(self.deck.pop())

    def _reshuffle_discard_into_deck(self) -> None:
        self.deck, self.discard_pile = self.discard_pile, []
        random.shuffle(self.deck)

    def discard_card(self, card: Card) -> bool:
        """Removes a card from hand and moves to the discard pile."""
        if card in self.hand:
            self.hand.remove(card)
            self.discard_pile.append(card)
            return True
        return False

    def add_bullet_card(self) -> None:
        """Called when this bandit gets shot - a neutral bullet card gets
        mixed into their discard pile, so it re-enters their deck on the
        next reshuffle and clogs their hand."""
        self.discard_pile.append(BulletCard())

    def new_round_reset(self) -> None:
        """Shuffle everything (hand + deck + discard) back into a fresh
        deck and draw a new hand - this happens at the start of every
        round in the base game."""
        self.deck = self.hand + self.deck + self.discard_pile
        self.hand = []
        self.discard_pile = []
        random.shuffle(self.deck)
        self.draw(self.hand_size)
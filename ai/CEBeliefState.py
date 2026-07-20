# belief_state.py
"""
Per-agent memory. This is the "Phase 1" side of the POMDP split described
in engine/CEObservation.py: choose_action() (Phase 2) only ever sees the
current Observation plus whatever a BeliefState has accumulated across
past Observations - never the raw GameState.

v1 keeps this deliberately simple, per the design brief: deck composition
is fixed and public, so tracking an opponent's likely remaining cards is
plain card-counting (no real probability distribution needed). Loot value
estimation gets a similar treatment: Observation reveals a piece's *kind*
(Purse / Jewel / Strongbox), and Jewel/Strongbox always have a fixed
value, so those are exact once the kind is known. Only a Purse's value
(250/300/350/400/450/500) is genuinely hidden, so that's the one case
that needs an estimate - a flat population average rather than a full
probability distribution.
"""

from typing import List, Dict

from engine.CEObservation import Observation, PublicCar
from models.CECards import BASE_DECK_COMPOSITION, CardType
from models.CETrain import LootType, PURSE_POOL, JEWEL_VALUE, STRONGBOX_VALUE

# Only a Purse's value is actually uncertain - Jewel and Strongbox are
# fixed. This is the "no real probabilistic inference in v1" approximation
# thge design calls for
_AVERAGE_PURSE_VALUE = sum(PURSE_POOL) / len(PURSE_POOL)

_KNOWN_VALUES = {
    LootType.JEWEL: JEWEL_VALUE,
    LootType.STRONGBOX: STRONGBOX_VALUE
}


class BeliefState:
    def __init__(self, self_name: str, opponent_names: List[str]):
        self.self_name = self_name
        # Track what cards opponents likely have left
        self.opponent_decks = {name: self._init_base_deck() for name in opponent_names}
    
    def _init_base_deck(self) -> dict:
        """Returns a fresh copy of the standard starting card counts for a
        bandit. Must be a copy - handing out the same dict to every
        opponent would mean decrementing one opponent's estimated deck
        silently decrements everyone else's too."""
        return dict(BASE_DECK_COMPOSITION)
    
    def estimate_piece_value(self, kind: LootType) -> float:
        """Expected value of a single loot piece of the given kind.
        Exact for Jewel/Strongbox (their value is fixed); a population
        average for Purse (the one kind whose value is still hidden)."""
        return _KNOWN_VALUES.get(kind, _AVERAGE_PURSE_VALUE)

    def estimate_car_value(self, car: PublicCar) -> float:
        """Expected total value of the unlooted loot sitting in `car`
        (inside + roof combined), from its publicly-visible loot dictionary."""
        total_value = 0.0

        for loot_type, count in car.loot_inside.items():
            total_value += self.estimate_piece_value(loot_type) * count

        for loot_type, count in car.loot_roof.items():
            total_value += self.estimate_piece_value(loot_type) * count

        return total_value

    def estimate_carried_value(self, loot_dict: Dict[LootType, int]) -> float:
        """
        Expected total value of a face-down pile given as a dictionary 
        of {LootType: count}.
        """
        total_value = 0.0
        for loot_type, count in loot_dict.items():
            total_value += self.estimate_piece_value(loot_type) * count
        return total_value
    
    def update(self, obs: Observation):
        """
        Phase 1: Memory update
        Reconcile the persistent belief with new public data.
        """
        
        # Observe if card counting needs a reset based on shuffle
        for name, bandit in obs.bandits.items():
            if name == self.self_name:
                continue

            # Logic: If the total cards (hand + deck) suddenly increase,
            # they performed a deck reset (shuffle).
            # Reset their deck tracking to the full base composition.
            total_known_cards = bandit.hand_size + bandit.deck_size
            if total_known_cards > sum(self.opponent_decks[name].values()):
                self.opponent_decks[name] = self._init_base_deck()

        # Card counting based on public plays
        for play in obs.plays_seen_this_round:
            if play.bandit_name != self.self_name and play.card_type is not None:
                # Deduct the seen card from their assumed deck
                self._record_card_played(play.bandit_name, play.card_type)

        # TODO: Add logic to estimate opponent positions based on seen cards

    def _record_card_played(self, bandit_name: str, card_type: CardType):
        """
        Deducts the observed card from the opponent's estimated deck.
        If the count drops below zero (impossible in a perfect game),
        it signals a discrepancy (e.g., they drew or a shuffle occurred)
        """
        if bandit_name in self.opponent_decks:
            deck = self.opponent_decks[bandit_name]
            if deck.get(card_type, 0) > 0:
                deck[card_type] -= 1
            else:
                # Log or handle discrepany:
                # This happens if an opponent plays more cards than standard
                # or if your tracking needs a reset after a full deck shuffle.
                pass
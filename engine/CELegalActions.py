# CELegalActions.py
"""
"""

from typing import List

from engine import CERules
from engine.CEActions import Action
from engine.CEGameState import GameState
from models.CECards import Card


def legal_actions_for(state: GameState, bandit_name: str) -> List[Action]:
    bandit = state.bandits.get(bandit_name)
    if bandit is None:
        return []
    
    playable_cards = [c for c in state.cards[bandit_name].hand if isinstance(c, Card)]
    actions: List[Action] = []

    for card in playable_cards:
        actions.extend(_candidates_for_card(state, bandit_name, card))

    return actions


def _candidates_for_card(state: GameState, bandit_name: str, card: Card) -> List[Action]:
    from models.CECards import CardType

    bandit = state.bandits[bandit_name]
    out: List[Action] = []

    if card.type == CardType.MOVE:
        for target_car in state.train.neighbors(bandit.current_car_id):
            if CERules.can_move(state, bandit_name, target_car):
                out.append(Action.from_card(bandit_name, card, target_car=target_car))

    elif card.type == CardType.CLIMB:
        if CERules.can_climb(state, bandit_name):
            out.append(Action.from_card(bandit_name, card))

    elif card.type == CardType.LOOT:
        if CERules.can_loot(state, bandit_name):
            out.append(Action.from_card(bandit_name, card))

    elif card.type == CardType.PUNCH:
        for victim_name in state.active_bandit_names():
            if victim_name == bandit_name:
                continue
            if not CERules.can_punch(state, bandit_name, victim_name):
                continue
            victim = state.bandits[victim_name]
            knockback_options = state.train.neighbors(victim.current_car_id) or [victim.current_car_id]
            for knockback_car in knockback_options:
                out.append(Action.from_card(bandit_name, card, target_bandit=victim_name,
                                             target_car=knockback_car))

    elif card.type == CardType.SHOOT:
        for victim_name in state.active_bandit_names():
            if victim_name == bandit_name:
                continue
            if CERules.can_shoot(state, bandit_name, victim_name):
                out.append(Action.from_card(bandit_name, card, target_bandit=victim_name))

    elif card.type == CardType.MARSHAL:
        for direction in (-1, 1):
            if CERules.can_move_marshal(state, bandit_name, direction):
                out.append(Action.from_card(bandit_name, card, direction=direction))

    return out
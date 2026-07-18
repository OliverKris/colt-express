# CEGameManager.py
"""
Runs a full base-game: for each of the game's rounds, plays through every
Turn defined on that round's Round card (Schemin' phase, collecting one
Action per bandit per turn into a shared stack), then resolves the whole
stack in play order (Stealin' phase).
"""

from typing import Callable, List, Optional

from engine.CEActions import Action
from engine.CEGameRounds import Turn, TurnType
from engine.CEGameState import GameState
from engine.CETurnResolution import resolve_action

# Given the current state, whose turn it is, and which Turn slot we're in,
# return the Action they want to take, or None to skip-and-draw-3 instead.
ActionChooser = Callable[[GameState, str, Turn], Optional[Action]]

def _play_one_action(state: GameState, bandit_name: str, turn: Turn,
                     choose: ActionChooser, stack: List[Action]) -> None:
    bandit = state.bandits[bandit_name]
    if not bandit:
        return
    
    action = choose(state, bandit_name, turn)
    player_cards = state.cards[bandit_name]

    if action is None:
        player_cards.draw(3)
        state.log.append(f"{bandit_name}: skipped turn {turn.turn_num} to draw 3 cards")
        return

    if action.card not in player_cards.hand:
        # Defensive: a misbehaving chooser tried to play a card it doesn't have.
        # Treat ist as a skip rather than corrupting the game state.
        state.log.append(f"{bandit_name}: tried to play a card not in hand - treated as a skip")
        player_cards.draw(3)
        return
    
    player_cards.discard_card(action.card)
    if turn.turn_type == TurnType.TUNNEL:
        state.log.append(f"{bandit_name}: played a card face-down (Tunnel turn)")
    stack.append(action)


def run_turn(state: GameState, turn: Turn, choose: ActionChooser, stack: List[Action]):
    order = state.turn_order_for_round(reversed_order=(turn.turn_type == TurnType.SWITCH))
    plays_per_bandit = 2 if turn.turn_type == TurnType.SPEED else 1

    for _ in range(plays_per_bandit):
        for bandit_name in order:
            _play_one_action(state, bandit_name, turn, choose, stack)

def run_round(state: GameState, choose: ActionChooser) -> None:
    for pc in state.cards.values():
        pc.new_round_reset

    stack: List[Action] = []
    for turn in state.current_round.turns:
        run_turn(state, turn, choose, stack)

    # Stealin' phase: resolve everything played this round, in order.
    for action in stack:
        resolve_action(state, action)
    
    # TODO: Implement end-of-round effects
    if state.current_round.eor_effect:
        state.log.append(f"[unimplemented end-of-round effect: {state.current_round.eor_effect}]")

    state.round_index += 1
    state.first_player_index = (state.first_player_index + 1) % len(state.seating_order)


def play_game(state: GameState, choose: ActionChooser) -> dict:
    """Runs every remaining round and returns final scores."""
    while not state.is_game_over():
        run_round(state, choose)
    return state.final_scores()
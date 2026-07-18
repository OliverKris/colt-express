# CEGameManager.py
"""
Runs a full base-game: for each of the game's rounds, plays through every
Turn defined on that round's Round card (Schemin' phase, collecting one
Action per bandit per turn onto state.round_stack), then resolves the
whole stack in play order (Stealin' phase).

state.round_stack (rather than a locally-threaded list) is what lets
CEObservation.py show a bandit what's been played so far *this round* by
bandits who acted earlier in turn order - the raw material for an agent's
"guess what/where other agents are doing" step.
"""

from typing import Callable, Optional

from engine.CEActions import Action
from engine.CEGameRounds import StackEntry, Turn, TurnType
from engine.CEGameState import GameState
from engine.CETurnResolution import resolve_action

# Given the current state, whose turn it is, and which Turn slot we're in,
# return the Action they want to take, or None to skip-and-draw-3 instead.
ActionChooser = Callable[[GameState, str, Turn], Optional[Action]]

def _play_one_action(state: GameState, bandit_name: str, turn: Turn,
                     choose: ActionChooser) -> None:
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
    state.round_stack.append(StackEntry(action=action, turn=turn))


def run_turn(state: GameState, turn: Turn, choose: ActionChooser):
    order = state.turn_order_for_round(reversed_order=(turn.turn_type == TurnType.SWITCH))
    plays_per_bandit = 2 if turn.turn_type == TurnType.SPEED else 1

    for _ in range(plays_per_bandit):
        for bandit_name in order:
            _play_one_action(state, bandit_name, turn, choose)

def run_round(state: GameState, choose: ActionChooser) -> None:
    # Base game has no elimination concept - every bandit resets each round.
    for pc in state.cards.values():
        pc.new_round_reset()

    state.round_stack = []
    for turn in state.current_round.turns:
        run_turn(state, turn, choose)

    # Stealin' phase: resolve everything played this round, in order.
    for entry in state.round_stack:
        resolve_action(state, entry.action)
    
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
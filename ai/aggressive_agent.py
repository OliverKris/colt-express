# aggressive_agent.py
"""
An aggressive HeuristicAgent variant: prioritizes shooting and punching
rivals - especially whoever is currently carrying the most loot - over
quietly collecting loot for itself.

This is a worked example of *both* customization paths described in
heuristic_agent.py's docstring:
    1. AGGRESSIVE_WEIGHTS retunes the numbers (more reward for combat,
       less for looting) without touching any logic.
    2. score_shoot / score_punch are overridden outright to add
       "focus fire the leader" behavior that isn't expressible as a
       weight on the base class.
Candidate generation and pick-the-max are inherited from HeuristicAgent
for free.
"""

from typing import Optional

from ai.heuristic_agent import HeuristicAgent, HeuristicWeights
from engine.CEActions import Action
from engine.CEGameState import GameState


AGGRESSIVE_WEIGHTS = HeuristicWeights(
    loot_value_scale=0.6,           # still loots, just less eagerly
    move_toward_loot_scale=15.0,

    climb_base=10.0,
    climb_roof_loot_bonus=40.0,

    punch_base=60.0,                # punching is nearly always worth it
    punch_steal_scale=1.2,

    shoot_base=220.0,                # shooting is the top priority
    shoot_loot_denial_scale=0.6,

    marshal_base=5.0,
    marshal_hit_rival_bonus=140.0,
    marshal_self_penalty=200.0,

    random_jitter=5.0,
)


class AggressiveAgent(HeuristicAgent):
    """Leans hard into combat rather than passively collecting loot."""

    name = "aggressive"

    def __init__(self, weights: Optional[HeuristicWeights] = None, seed: Optional[int] = None):
        super().__init__(weights=weights or AGGRESSIVE_WEIGHTS, seed=seed)

    def score_shoot(self, state: GameState, bandit_name: str, action: Action) -> float:
        base = super().score_shoot(state, bandit_name, action)

        # Focus fire whoever is currently holding the most loot, not just
        # whichever rival happens to be in range.
        victim = state.bandits[action.target_bandit]
        rival_totals = [b.total_loot_value() for n, b in state.bandits.items() if n != bandit_name]
        leader_value = max(rival_totals, default=0)
        if leader_value > 0 and victim.total_loot_value() == leader_value:
            base += self.weights.shoot_base * 0.5

        return base

    def score_punch(self, state: GameState, bandit_name: str, action: Action) -> float:
        base = super().score_punch(state, bandit_name, action)

        # Extra incentive to punch someone who's holding loot, since the
        # punch also knocks a piece of it loose.
        victim = state.bandits[action.target_bandit]
        if victim.loot:
            base += 15.0

        return base
# CEAggressiveAgent.py
"""
Combat-focused HeuristicAgent: prefers shooting/punching loot-heavy
opponents over looting cars itself, and shows a slight preference for
spending its last bullet to lock in the Gunslinger bonus.
"""

from typing import List, Optional

from ai.CEHeuisticAgent import HeuristicAgent
from ai.CEBeliefState import BeliefState
from engine.CEActions import Action, ActionType
from engine.CEObservation import Observation


class AggressiveAgent(HeuristicAgent):
    name = "aggressive"

    def __init__(self, name: str, all_bandit_names: List[str], seed: Optional[int] = None):
        super().__init__(
            name=name,
            all_bandit_names=all_bandit_names,
            scorers=[
                self._score_shooting,
                self._score_punching,
                self._score_looting,
                self._score_gunslinger_push,
            ],
            weights=[1.0, 0.6, 0.3, 0.4],
            seed=seed,
            jitter=0.05,
        )

    def _score_shooting(self, obs: Observation, belief: BeliefState, action: Action) -> float:
        """Prefer shooting whoever is carrying the most estimated loot -
        doesn't steal it, but a bullet card clogging their deck slows
        their next few turns down."""
        if action.type != ActionType.SHOOT:
            return 0.0
        victim = obs.bandits[action.target_bandit]
        return belief.estimate_carried_value(victim.carried_loot) / 100.0

    def _score_punching(self, obs: Observation, belief: BeliefState, action: Action) -> float:
        """Punching a loot carrier knocks one of their pieces loose into
        whatever car they land in - not a steal, but it strips their
        stash and leaves a piece sitting somewhere we can go pick up."""
        if action.type != ActionType.PUNCH:
            return 0.0
        victim = obs.bandits[action.target_bandit]
        if not victim.carried_loot:
            return 0.0
        return belief.estimate_carried_value(victim.carried_loot) / 150.0

    def _score_looting(self, obs: Observation, belief: BeliefState, action: Action) -> float:
        """Secondary priority - loot if there's nothing worth shooting."""
        if action.type != ActionType.LOOT:
            return 0.0
        bandit = obs.bandits[obs.self_name]
        car = obs.car(bandit.current_car_id)
        if car is None:
            return 0.0
        pile = car.loot_roof if bandit.is_on_roof else car.loot_inside
        if not pile:
            return 0.0
        return belief.estimate_carried_value(pile)

    def _score_gunslinger_push(self, obs: Observation, belief: BeliefState, action: Action) -> float:
        """Slight nudge toward firing the last bullet - the 1000-point
        Gunslinger bonus is worth more than most single loot pieces."""
        if action.type != ActionType.SHOOT:
            return 0.0
        self_bandit = obs.bandits[obs.self_name]
        if self_bandit.bullets_remaining == 1 and obs.gunslinger is None:
            return 1000.0
        return 0.0
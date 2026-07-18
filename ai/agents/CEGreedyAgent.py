# CEGreedyAgent.py

from typing import Optional, List
from ai.CEHeuisticAgent import HeuristicAgent
from engine.CEObservation import Observation
from ai.CEBeliefState import BeliefState
from engine.CEActions import Action, ActionType
from models.CETrain import LootType

class GreedyAgent(HeuristicAgent):
    """Chases loot value greedily. Observation exposes each loot piece's
    *kind* (Purse/Jewel/Strongbox) but never its value - scoring goes
    through BeliefState.estimate_piece_value()/estimate_car_value(), which
    are exact for Jewel/Strongbox and use a population average for the
    one kind (Purse) whose value is still genuinely hidden."""

    name = "greedy"

    def __init__(self, name: str, all_bandit_names: List[str], seed: Optional[int] = None):
        super().__init__(
            name=name,
            all_bandit_names=all_bandit_names,
            scorers=[self._score_looting, self._score_navigation],
            weights=[1.0, 0.5],
            seed=seed,
            jitter=0.05,
        )

    def _score_looting(self, obs: Observation, belief: BeliefState, action: Action) -> float:
        """Rewards the Loot action by the expected value of the single
        piece it would pick up (not the whole car - only one piece is
        looted per LOOT action, and CETurnResolution always takes the
        last piece in the pile, so we can score that exact piece's known
        kind rather than averaging over the whole side)."""
        if action.type != ActionType.LOOT:
            return 0.0
        
        bandit = obs.bandits[obs.self_name]
        car = obs.car(bandit.current_car_id)
        if car is None:
            return 0.0

        # Estimate the loot value
        loot_pool = car.loot_roof if bandit.is_on_roof else car.loot_inside
        if loot_pool is None:
            return 0.0

        return belief.estimate_carried_value(loot_pool)

    def _score_navigation(self, obs: Observation, belief: BeliefState, action: Action) -> float:
        """Values moving/climbing toward a car by its total expected loot,
        as a rough "worth heading that way" signal."""
        if action.type not in (ActionType.MOVE, ActionType.CLIMB):
            return 0.0
        
        target_id = action.target_car if action.target_car != -1 else obs.bandits[obs.self_name].current_car_id
        car = obs.car(target_id)
        if car is None:
            return 0.0

        return belief.estimate_car_value(car)
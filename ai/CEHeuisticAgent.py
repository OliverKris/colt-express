# CEHeuristicAgent.py
"""
An AI heuristic agent template
"""

import random
from typing import List, Optional, Tuple, Callable

from ai.CEBaseAgent import Agent
from engine.CEActions import Action
from engine.CEGameRounds import Turn
from engine.CEObservation import Observation, legal_actions_for_observation
from ai.belief_state import BeliefState

# A Scorer takes the current view of the world and the proposed action
# and returns a float score.
Scorer = Callable[[Observation, BeliefState, Action], float]

class HeuristicAgent(Agent):
    def __init__(self, name: str, all_bandit_names: List[str], 
                 scorers: List[Scorer], weights: List[float], 
                 seed: Optional[int] = None, jitter: float = 0.05):
        super().__init__(name, all_bandit_names)
        
        self.scorers = scorers  # List of functions
        self.weights = weights  # Multiplier for each function
        self.jitter = jitter
        self._rng = random.Random(seed)

    def _score(self, obs: Observation, belief: BeliefState, action: Action) -> float:
        total = sum(s(obs, belief, action) * w for s, w in zip(self.scorers, self.weights))
        return total + random.uniform(-self.jitter, self.jitter)

    def choose_action(self, obs: Observation, belief: BeliefState, turn: Turn) -> Optional[Action]:
        candidates = legal_actions_for_observation(obs)
        if not candidates:
            return None
        
        scored: List[Tuple[float, Action]] = [
            (self._score(obs, belief, action), action) for action in candidates
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[0][1]
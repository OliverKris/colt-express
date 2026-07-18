# CERandomAgent.py
"""
Simplest possible Agent - a uniform random choice among legal actions.
Good as a smoke-test opponent and as a template for new agents: this is
the minimum an Agent subclass needs to implement.
"""

import random
from typing import Optional, List

from ai.CEBaseAgent import Agent
from ai.belief_state import BeliefState
from engine.CEObservation import Observation, legal_actions_for_observation
from engine.CEActions import Action
from engine.CEGameRounds import Turn


class RandomAgent(Agent):
    name = "random"

    def __init__(self, name: str, all_bandit_names: List[str]):
        super().__init__(name, all_bandit_names)

    def choose_action(self, obs: Observation, belief: BeliefState, turn: Turn) -> Optional[Action]:
        candidates = legal_actions_for_observation(obs)
        if not candidates:
            return None
        return random.choice(candidates)
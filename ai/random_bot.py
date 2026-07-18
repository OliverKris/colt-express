# random_bot.py
"""
Simplest possible Agent - a uniform random choice among legal actions.
Good as a smoke-test opponent and as a template for new agents: this is
the minimum an Agent subclass needs to implement.
"""

import random
from typing import Optional

from ai.base_agent import Agent
from engine.CEActions import Action
from engine.CEGameRounds import Turn
from engine.CEGameState import GameState
from engine.CELegalActions import legal_actions_for


class RandomAgent(Agent):
    name = "random"

    def choose_action(self, state, bandit_name, turn) -> Optional[Action]:
        candidates = legal_actions_for(state, bandit_name)
        if not candidates:
            return None
        return random.choice(candidates)
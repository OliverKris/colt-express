# CEBaseAgent.py
"""
Every AI is a subclass of Agent. The engine (CSGameManager.ActionChooser)
only ever calls `agent(state, bandit_name, turn)`, so anything that
implements __call__ with this signature is a drop-in agent

To build a new AI: subclass Agent, implement choose_action().
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from engine.CEActions import Action
from engine.CEGameRounds import Turn
from engine.CEGameState import GameState
from engine.CEObservation import Observation, build_observation
from ai.belief_state import BeliefState


class Agent(ABC):
    """Base class for anything that plays bandits."""

    def __init__(self, name: str, all_bandit_names: List[str]):
        self.name = name
        # Agent maintains its own belief/memory of the game
        self.belief = BeliefState(
            self_name=name,
            opponent_names=[n for n in all_bandit_names if n != name]
        )

    @abstractmethod
    def choose_action(self, obs: Observation, belief: BeliefState, turn: Turn) -> Optional[Action]:
        """
        Subclasses implement this using ONLY the Observation and BeliefState.
        They no longer have access to the full GameState.
        """
        raise NotImplementedError
    
    def __call__(self, state: GameState, bandit_name: str, turn: Turn) -> Optional[Action]:
        """
        The gatekeeper: 
        1. Converts raw state to Observation.
        2. Updates the agent's internal BeliefState.
        3. Passes redacted data to the subclass logic.
        """
        
        obs = build_observation(state, self.name, turn)
        self.belief.update(obs)    
        return self.choose_action(obs, self.belief, turn)    
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}"
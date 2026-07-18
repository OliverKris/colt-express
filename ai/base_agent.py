# base_agent.py
"""
Every AI is a subclass of Agent. The engine (CSGameManager.ActionChooser)
only ever calls `agent(state, bandit_name, turn)`, so anything that
implements __call__ with this signature is a drop-in agent

To build a new AI: subclass Agent, implement choose_action().
"""

from abc import ABC, abstractmethod
from typing import Optional

from engine.CEActions import Action
from engine.CEGameRounds import Turn
from engine.CEGameState import GameState


class Agent(ABC):
    """Base class for anything that plays bandits."""

    #: Short identifier used by main.py's --agents flags and the registery
    name: str = "agent"

    @abstractmethod
    def choose_action(self, state: GameState, bandit_name: str, turn: Turn) -> Optional[Action]:
        """Return the Action to play this turn, or None to skip-and-draw-3."""
        raise NotImplemented
    
    def __call__(self, state: GameState, bandit_name: str, turn: Turn) -> Optional[Action]:
        return self.choose_action(state, bandit_name, turn)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}"
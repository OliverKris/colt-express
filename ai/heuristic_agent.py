# heuristic_agent.py
"""
A scored-heuristic Agent. Two ways to customize without touching the
engine or other agents:

    1. Pass a different HeuristicWeights() to the constructor to retune
       numbers.
    2. Subclass HeuristicAgent and override individual score_move /
       score_climb / score_loot / score_punch / score_shoot / score_marshal
       methods to change *how* and action type is evaluated, not just its
       weight. Everything else (candidate generation, picking the max) is
       inherited for free.

See ai/aggressive_agent.py for a worked example of approach #2.
"""

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ai.base_agent import Agent
from engine.CEActions import Action
from engine.CEGameRounds import Turn
from engine.CEGameState import GameState
from engine.CELegalActions import legal_actions_for


@dataclass
class HeuristicWeights:
    """Every number an out-of-the-box HeuristicAgent decision depends on.
    Tune these to change play style without writing any new code."""

    loot_value_scale: float = 1.0           # $ value of loot -> score, when looting
    move_toward_loot_scale: float = 30.0    # reward per car closer to the nearest loot

    climb_base: float = 10.0
    climb_roof_loot_bonus: float = 80.0     # extra reward if flipping reveals loot here

    punch_base: float = 20.0
    punch_steal_scale: float = 0.6          # reward scaled by the victim's carried loot value

    shoot_base: float = 150.0               # shooting is inherently valuable (denies opponent
                                            # a turn's worth of hand quality via a wound card)
    shoot_loot_denial_scale: float = 0.2    # extra reward if the victim is carrying loot

    marshal_base: float = 5.0
    marshal_hit_rival_bonus: float = 100.0  # per rival caught in the car the Marshal moves into
    marshal_self_penalty: float = 150.0     # avoid walking the Marshal onto yourself

    random_jitter: float = 5.0              # small noise so ties (and near-ties) aren't robotic


class HeuristicAgent(Agent):
    name = "heuristic"

    def __init__(self, weights: Optional[HeuristicWeights] = None, seed: Optional[int] = None):
        self.weights = weights or HeuristicWeights()
        self._rng = random.Random(seed)

    def choose_action(self, state: GameState, bandit_name: str, turn: Turn) -> Optional[Action]:
        candidates = legal_actions_for(state, bandit_name)
        if not candidates:
            return None
        scored: List[Tuple[float, Action]] = [
            (self._score(state, bandit_name, action), action) for action in candidates
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[0][1]

    def _score(self, state: GameState, bandit_name: str, action: Action) -> float:
        method = getattr(self, f"score_{action.type.name.lower()}", None)
        base = method(state, bandit_name, action) if method else 0.0
        return base + self._rng.uniform(-self.weights.random_jitter, self.weights.random_jitter)

    def score_move(self, state: GameState, bandit_name: str, action: Action) -> float:
        bandit = state.bandits[bandit_name]
        current_dist = self._nearest_loot_distance(state, bandit.current_car_id)
        new_dist = self._nearest_loot_distance(state, action.target_car)
        if current_dist is None or new_dist is None:
            return 0.0
        improvement = current_dist - new_dist
        return improvement * self.weights.move_toward_loot_scale

    def score_climb(self, state: GameState, bandit_name: str, action: Action) -> float:
        bandit = state.bandits[bandit_name]
        car = state.train.get_car(bandit.current_car_id)
        flipped_loot = car.loot_at(not bandit.is_on_roof)
        bonus = self.weights.climb_roof_loot_bonus if flipped_loot else 0.0
        return self.weights.climb_base + bonus

    def score_loot(self, state: GameState, bandit_name: str, action: Action) -> float:
        bandit = state.bandits[bandit_name]
        car = state.train.get_car(bandit.current_car_id)
        pool = car.loot_at(bandit.is_on_roof)
        best_value = max((item.value for item in pool), default=0)
        return best_value * self.weights.loot_value_scale

    def score_punch(self, state: GameState, bandit_name: str, action: Action) -> float:
        victim = state.bandits[action.target_bandit]
        return self.weights.punch_base + victim.total_loot_value() * self.weights.punch_steal_scale

    def score_shoot(self, state: GameState, bandit_name: str, action: Action) -> float:
        victim = state.bandits[action.target_bandit]
        return self.weights.shoot_base + victim.total_loot_value() * self.weights.shoot_loot_denial_scale

    def score_marshal(self, state: GameState, bandit_name: str, action: Action) -> float:
        target_car = state.marshal.current_car_id + action.direction
        occupants = state.bandit_at(target_car, on_roof=False)
        rivals_hit = [n for n in occupants if n != bandit_name]
        score = self.weights.marshal_base + len(rivals_hit) * self.weights.marshal_hit_rival_bonus
        if bandit_name in occupants:
            score -= self.weights.marshal_self_penalty
        return score

    @staticmethod
    def _nearest_loot_distance(state: GameState, car_id: int) -> Optional[int]:
        lootable = [c.id for c in state.train.cars if c.loot_inside or c.loot_roof]
        if not lootable:
            return None
        return min(abs(cid - car_id) for cid in lootable)
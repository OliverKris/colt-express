# CEMCTSAgent.py
"""
Single-Observer Information-Set MCTS (SO-ISMCTS) with Perfect-Information
Monte Carlo (PIMC) determinization: the standard approach for running
tree search in a game with hidden information, without the tree itself
ever needing to see that hidden information.

One tree is kept per call to choose_action, but every simulation samples
its own concrete "possible world" (ai/CEDeterminize.py) consistent with
this agent's BeliefState, searches/rolls out through *that*, then throws
it away. Nothing in the tree - node values, UCB scores, visit counts -
is ever computed from anything but these sampled worlds, so the search
can never learn something a real bandit couldn't have known.

Search shape, one call to choose_action:
    1. Selection   - walk down existing tree nodes via UCB1 while they're
                     already fully expanded.
    2. Expansion   - at the first not-fully-expanded node reached, add one
                     new child for one untried action. Exactly one
                     expansion per simulation, same as vanilla MCTS.
    3. Rollout     - from there, keep driving the real engine forward
                     (finish the current round, then up to
                     `search_depth_rounds` more full rounds) using a cheap
                     default policy for both ourselves and everyone else -
                     no more tree bookkeeping past this point.
    4. Backprop    - evaluate the resulting world with a heuristic (exact
                     final score if the game genuinely ended within the
                     horizon) and back the value up every node visited.
Repeat for num_simulations, then play the root's most-visited child
(the "robust child" - more stable under noisy value estimates than
picking by raw average value).

Opponents are never given their own search - they're simulated with a
plain Agent instance (default: RandomAgent) both during rollout AND for
any of *their* decisions the tree walks through. Since any Agent already
builds its own Observation from whatever GameState it's handed, this is
non-negotiably honest for free: an opponent stand-in still can't see
anyone else's hand even inside our simulation.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from ai.CEBaseAgent import Agent
from ai.CEBeliefState import BeliefState
from ai.CEDeterminize import determinize
from ai.agents.CERandomAgent import RandomAgent
from engine.CEActions import Action
from engine.CEGameManager import _play_one_action, run_round, run_turn
from engine.CEGameRounds import Turn, TurnType
from engine.CEGameState import GameState
from engine.CELegalActions import legal_actions_for
from engine.CEObservation import Observation, build_observation, legal_actions_for_observation
from engine.CETurnResolution import resolve_action

PolicyFactory = Callable[[str], Agent]


@dataclass
class MCTSNode:
    action: Optional[Action] = None
    parent: Optional["MCTSNode"] = None
    children: List["MCTSNode"] = field(default_factory=list)
    untried_actions: Optional[List[Action]] = None  # None = not yet visited
    visits: int = 0
    total_value: float = 0.0

    def ucb_score(self, c: float) -> float:
        if self.visits == 0:
            return float("inf")
        exploit = self.total_value / self.visits
        explore = c * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploit + explore

    def best_child(self, c: float) -> "MCTSNode":
        return max(self.children, key=lambda child: child.ucb_score(c))


class MCTSAgent(Agent):
    """The 'honest' search agent: never reads GameState from inside a
    decision, only from the narrowly-scoped determinizer (see
    ai/CEDeterminize.py's docstring for exactly what that's allowed to
    touch)."""

    name = "mcts"

    def __init__(
        self,
        name: str,
        all_bandit_names: List[str],
        opponent_policy_factory: Optional[PolicyFactory] = None,
        rollout_policy_factory: Optional[PolicyFactory] = None,
        search_depth_rounds: int = 0,
        num_simulations: int = 200,
        exploration_c: float = 1.4,
        seed: Optional[int] = None,
    ):
        super().__init__(name, all_bandit_names)
        self.all_bandit_names = all_bandit_names
        # Default: a plain RandomAgent stands in for anyone we don't
        # search - the standard cheap default policy in MCTS. Swap in a
        # stronger stand-in (e.g. GreedyAgent) via these factories to see
        # how search quality responds to a more realistic opponent model.
        self.opponent_policy_factory = opponent_policy_factory or (
            lambda n: RandomAgent(name=n, all_bandit_names=all_bandit_names)
        )
        self.rollout_policy_factory = rollout_policy_factory or (
            lambda n: RandomAgent(name=n, all_bandit_names=all_bandit_names)
        )
        self.search_depth_rounds = search_depth_rounds
        self.num_simulations = num_simulations
        self.c = exploration_c
        self._rng = random.Random(seed)

    # ---- Agent interface ----

    def __call__(self, state: GameState, bandit_name: str, turn: Turn) -> Optional[Action]:
        # Same Phase-1 gatekeeping every Agent does. The search below
        # additionally needs the real GameState to build sampled worlds
        # from - that's the one deliberately-scoped exception in this
        # whole AI stack; see ai/CEDeterminize.py.
        obs = build_observation(state, self.name, turn)
        self.belief.update(obs)
        return self._search(state, obs, turn)

    def choose_action(self, obs: Observation, belief: BeliefState, turn: Turn) -> Optional[Action]:
        """Never called for our own top-level decisions (see __call__
        above) - this exists so MCTSAgent satisfies Agent's abstract
        interface, and doubles as a cheap Observation-only fallback if
        anything ever calls it directly."""
        candidates = legal_actions_for_observation(obs)
        return self._rng.choice(candidates) if candidates else None

    # ---- search ----

    def _search(self, state: GameState, obs: Observation, turn: Turn) -> Optional[Action]:
        candidates = legal_actions_for_observation(obs)
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        root = MCTSNode()
        for _ in range(self.num_simulations):
            world = determinize(state, self.belief, self._rng)
            self._simulate(root, world, turn)

        if not root.children:
            return self._rng.choice(candidates)
        best = max(root.children, key=lambda child: child.visits)
        return best.action

    def _simulate(self, root: MCTSNode, world: GameState, turn: Turn) -> None:
        path = [root]
        node = root
        in_tree = True

        def choose(w: GameState, bname: str, t: Turn) -> Optional[Action]:
            nonlocal node, in_tree

            if bname != self.name:
                policy = self.opponent_policy_factory(bname)
                return policy(w, bname, t)

            if not in_tree:
                return self.rollout_policy_factory(self.name)(w, bname, t)

            if node.untried_actions is None:
                node.untried_actions = legal_actions_for(w, self.name)

            if node.untried_actions:
                idx = self._rng.randrange(len(node.untried_actions))
                action = node.untried_actions.pop(idx)
                child = MCTSNode(action=action, parent=node)
                node.children.append(child)
                path.append(child)
                node = child
                in_tree = False  # exactly one expansion per simulation
                return action

            if node.children:
                child = node.best_child(self.c)
                path.append(child)
                node = child
                return child.action

            return None  # no legal action here at all - treated as a skip

        self._finish_turn_from_here(world, turn, choose)
        for t in world.current_round.turns:
            if t.turn_num > turn.turn_num:
                run_turn(world, t, choose)
        self._finish_round_bookkeeping(world)

        for _ in range(self.search_depth_rounds):
            if world.is_game_over():
                break
            run_round(world, choose)

        value = self._evaluate(world)
        for n in path:
            n.visits += 1
            n.total_value += value

    @staticmethod
    def _finish_turn_from_here(world: GameState, turn: Turn, choose) -> None:
        """The real engine has already run everyone before us this turn
        (that's why we're being asked for an action at all) - resume from
        there instead of re-running the whole turn, which would
        double-count the bandits who already went."""
        order = world.turn_order_for_round(reversed_order=(turn.turn_type == TurnType.SWITCH))
        plays_per_bandit = 2 if turn.turn_type == TurnType.SPEED else 1
        slots = [name for _ in range(plays_per_bandit) for name in order]
        already_played = sum(1 for e in world.round_stack if e.turn.turn_num == turn.turn_num)
        for bandit_name in slots[already_played:]:
            _play_one_action(world, bandit_name, turn, choose)

    @staticmethod
    def _finish_round_bookkeeping(world: GameState) -> None:
        """Mirrors the tail of CEGameManager.run_round (Stealin' phase +
        round rotation) for the round we just manually finished."""
        for entry in world.round_stack:
            resolve_action(world, entry.action)
        world.round_index += 1
        if world.seating_order:
            world.first_player_index = (world.first_player_index + 1) % len(world.seating_order)

    def _evaluate(self, world: GameState) -> float:
        """Heuristic leaf value once the search horizon is reached - exact
        final score if the sampled game actually ended within it."""
        if world.is_game_over():
            return float(world.final_scores()[self.name])

        me = world.bandits[self.name]
        value = float(me.total_loot_value())
        if world.gunslinger == self.name:
            value += 1000.0
        elif world.gunslinger is None and me.bullets_remaining <= 1:
            value += 150.0  # one shot from locking in the Gunslinger bonus
        return value

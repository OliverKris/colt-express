#!/usr/bin/env python3
# main.py
"""
Entry point: simulates one or more games of Colt Express between AI agents
and reports the results.

Examples:
    python main.py
    python main.py --agents random random greedy aggressive
    python main.py --agents greedy aggressive --games 200 --seed 1
    python main.py --agents random random --games 1 --verbose
"""

import argparse
import statistics
from collections import Counter
from typing import Dict, List, Optional, Type

from ai.CEBaseAgent import Agent
from ai.agents.CERandomAgent import RandomAgent
from ai.agents.CEGreedyAgent import GreedyAgent
from ai.agents.CEAggressiveAgent import AggressiveAgent
from ai.agents.CEMCTSAgent import MCTSAgent
from engine.CEGameManager import play_game
from engine.CEGameState import GameState

AGENT_REGISTRY: Dict[str, Type[Agent]] = {
    "random": RandomAgent,
    "greedy": GreedyAgent,
    "aggressive": AggressiveAgent,
    "mcts": MCTSAgent,
}

# Matches models.CEPieces.BASE_BANDITS ordering (max 6 players).
BANDIT_NAMES = ["GHOST", "DOC", "TUCO", "CHEYENNE", "BELLE", "DJANGO"]


def build_agents(agent_kinds: List[str], seed: Optional[int]) -> Dict[str, Agent]:
    """One Agent instance per bandit, each with its own derived RNG seed
    so a run is reproducible but agents aren't all sampling in lockstep."""
    agents: Dict[str, Agent] = {}

    for i, kind in enumerate(agent_kinds):
        bandit_name = BANDIT_NAMES[i]

        if kind not in AGENT_REGISTRY:
            raise ValueError(f"Unknown agent type: {kind}")

        cls = AGENT_REGISTRY[kind]

        agents[bandit_name] = cls(name=bandit_name, all_bandit_names=BANDIT_NAMES)

    return agents


def run_one_game(agent_kinds: List[str], seed: Optional[int], verbose: bool) -> Dict[str, int]:
    bandit_names = BANDIT_NAMES[: len(agent_kinds)]
    agents = build_agents(agent_kinds, seed)
    state = GameState.new_game(bandit_names, seed=seed)

    def choose(state, bandit_name, turn):
        return agents[bandit_name](state, bandit_name, turn)

    scores = play_game(state, choose)

    if verbose:
        for line in state.log:
            print(line)
        print()

    return scores


def main():
    parser = argparse.ArgumentParser(description="Simulate Colt Express games between AI agents.")
    parser.add_argument(
        "--agents", nargs="+", default=["random", "aggressive", "greedy"],
        choices=list(AGENT_REGISTRY),
        help="One agent type per bandit, 2-6 entries (default: random random heuristic aggressive).",
    )
    parser.add_argument("--games", type=int, default=1, help="Number of games to simulate.")
    parser.add_argument("--seed", type=int, default=None, help="Base RNG seed for reproducibility.")
    parser.add_argument("--verbose", action="store_true", help="Print the full action log for each game.")
    args = parser.parse_args()

    if not (2 <= len(args.agents) <= len(BANDIT_NAMES)):
        parser.error(f"--agents needs between 2 and {len(BANDIT_NAMES)} entries (one per bandit).")

    wins: Counter = Counter()
    all_scores: Dict[str, List[int]] = {BANDIT_NAMES[i]: [] for i in range(len(args.agents))}

    for game_num in range(args.games):
        game_seed = None if args.seed is None else args.seed + game_num * 1000

        if args.verbose:
            print(f"===== Game {game_num + 1} (agents={args.agents}, seed={game_seed}) =====")

        scores = run_one_game(args.agents, game_seed, args.verbose)
        winner = max(scores, key=scores.get)
        wins[winner] += 1
        for name, val in scores.items():
            all_scores[name].append(val)

        if args.verbose or args.games == 1:
            print(f"Game {game_num + 1} final scores:")
            for name, val in sorted(scores.items(), key=lambda kv: -kv[1]):
                kind = args.agents[BANDIT_NAMES.index(name)]
                print(f"  {name:10s} ({kind:10s}): ${val}")
            print(f"  Winner: {winner}\n")

    if args.games > 1:
        print(f"===== Summary over {args.games} games =====")
        for i, kind in enumerate(args.agents):
            name = BANDIT_NAMES[i]
            scores = all_scores[name]
            win_rate = 100.0 * wins[name] / args.games
            print(
                f"  {name:10s} ({kind:10s}): "
                f"avg=${statistics.mean(scores):8.1f}  "
                f"wins={wins[name]:3d}/{args.games} ({win_rate:5.1f}%)"
            )


if __name__ == "__main__":
    main()

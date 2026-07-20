# CEDeterminize.py
"""
Turns the real (omniscient) GameState into one plausible *sampled* world
consistent with what a single bandit's BeliefState actually knows - the
"D" in PIMC (Perfect Information Monte Carlo). Ordinary full-information
search (CEGameManager.run_turn/run_round, CETurnResolution.resolve_action)
then runs on this sampled world exactly as it would on a real one. A
fresh world gets resampled every simulation, so the search never leans on
any single guess.

What gets resampled:
    - every OTHER bandit's hand + deck *contents* (sizes are kept exact -
      those are public - refilled from BeliefState's per-opponent
      remaining-card-type counts rather than the true cards)
    - the search's own bandit's *deck order* (contents are already known -
      it's their hand - but nobody, including the real player, knows the
      draw order of their own shuffled deck in advance, so that's
      legitimately re-randomized too)
    - every unlooted or carried Purse's value (Jewel/Strongbox values are
      fixed constants and thus public knowledge once the loot's *kind* is
      visible, so those are left untouched)

Deliberately-scoped exception: this module is the one place in the AI
stack that's handed the real GameState rather than an Observation. Its
whole job is to launder away anything genuinely hidden before a single
line of search or heuristic code touches the result - see CEMCTSAgent.py
for how narrowly that access is scoped (only inside __call__, only to
build this one sampled clone; choose_action itself never sees GameState).

Known simplification carried over from CEActions.py: a played action's
*target* is committed at Schemin' time in this engine (rather than
deferred to Stealin'-phase resolution like the physical game), so an
opponent's already-played-but-unresolved action this round is replayed
here with its true target rather than a re-sampled one. This is a small,
transient leak scoped to the remainder of the current round only, not
something search results improve toward exploiting - flagging it rather
than hiding it. A more rigorous v2 could re-derive a plausible alternate
target per such entry.
"""

import copy
import random

from ai.CEBeliefState import BeliefState
from engine.CEGameState import GameState
from models.CECards import BulletCard, Card
from models.CETrain import Loot, LootType, PURSE_POOL


def determinize(state: GameState, belief: BeliefState, rng: random.Random) -> GameState:
    """Clone `state` and resample everything hidden from `belief.self_name`."""
    world = copy.deepcopy(state)

    for name, player_cards in world.cards.items():
        if name == belief.self_name:
            rng.shuffle(player_cards.deck)  # contents known, draw order isn't
            continue
        _resample_hand_and_deck(player_cards, belief, name, rng)

    for car in world.train.cars:
        car.loot_inside = [_resample_if_purse(item, rng) for item in car.loot_inside]
        car.loot_roof = [_resample_if_purse(item, rng) for item in car.loot_roof]

    for bandit in world.bandits.values():
        bandit.loot = [_resample_if_purse(item, rng) for item in bandit.loot]

    return world


def _resample_hand_and_deck(player_cards, belief: BeliefState, name: str, rng: random.Random) -> None:
    """Refills one opponent's hand+deck from BeliefState's remaining
    card-type counts, keeping the true (public) total size."""
    target_total = len(player_cards.hand) + len(player_cards.deck)
    remaining_counts = belief.opponent_decks.get(name, {})
    pool = [Card(c_type) for c_type, count in remaining_counts.items() for _ in range(count)]

    if len(pool) > target_total:
        # Tunnel-turn plays hide their card type from BeliefState, so it
        # can over-count what's left. We know exactly one of these was
        # consumed, just not which - sampling down keeps that honest.
        pool = rng.sample(pool, target_total)
    elif len(pool) < target_total:
        # The remaining gap is almost certainly bullet cards mixed in from
        # being shot - BulletCard isn't tracked by BeliefState since it's
        # not part of any bandit's real 10-card deck.
        pool = pool + [BulletCard() for _ in range(target_total - len(pool))]

    rng.shuffle(pool)
    hand_size = len(player_cards.hand)
    player_cards.hand = pool[:hand_size]
    player_cards.deck = pool[hand_size:]


def _resample_if_purse(item: Loot, rng: random.Random) -> Loot:
    if item.kind != LootType.PURSE:
        return item  # Jewel/Strongbox values are fixed and public
    return Loot(kind=LootType.PURSE, value=rng.choice(PURSE_POOL))

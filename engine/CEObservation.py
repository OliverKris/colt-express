# CEObservation.py
"""
Builds the partial-information view a signle bandit is allowed to see.

GameState is the omniscient "world" - CEGameManager hands it in full to
whatever ActionChooser it's given (see CEGameManager.ActionChooser). The
Agent base class (ai/base_agent.py) is where that stops: Agent.__call__
converts GameState into an Observation *before* any subclass decision
code runs, so agents can never read hidden information by accident.

Public in the physical game (kept as-is):
    - every bandit's car + roof/inside position
    - the Marshal's position
    - the *kind* (Purse / Jewel / Strongbox) of every loot piece sitting
      in a car, and of every piece a bandit is carrying - loot cards show
      their kind on the back, just not their value
    - a badit's bullets_remaining (visibile on their player board)
    - the *size* of an opponent's hand / deck / discard pile
    - the *type* of any card played face-up onto this round's action
      stack so far (Tunnel-turn cards are face-down and stay hidden
      until they resolve)

Hidden (redacted here):
    - the exact contents of anyone else's hand, deck, or discard pile
    - the *value* of any loot piece, anywhere - in a car, carried by an
      opponent, or carried by yourself. Nobody learns a piece's value
      until it's scored at the end of the game, so even
      Observation.self_loot only ever gives you the kind of what you're
      carrying, never the value
    - the *target* of a played-but-unresolved action - in the physical
      game you don't decide who to shoot/punch/loot until the card
      actually resolves, not when you play it
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Counter

from engine.CEGameRounds import Turn, TurnType
from engine.CEGameState import GameState
from models.CECards import Card, CardType
from models.CETrain import Loot, LootType 

@dataclass(frozen=True)
class PublicCar:
    """A car as anyone at the table can see it; you can see how many loot
    tokens sit inside / on the roof, since the tokens themselves are visible
    objects on the board - you just can't see their values which are hidden
    until the end of hte game."""
    id: int
    is_locomotive: bool
    loot_inside: Dict[LootType, int]
    loot_roof: Dict[LootType, int]


@dataclass(frozen=True)
class PublicBandit:
    """An opponent as anyone can see them: position and bullet count are
    plainly visible, and carried loot is visibile as face-down tokens in
    front of them (countable, not readable)."""
    name: str
    current_car_id: int
    is_on_roof: bool
    carried_loot: Dict[LootType, int]
    bullets_remaining: int
    hand_size: int
    deck_size: int
    discard_size: int


@dataclass(frozen=True)
class SeenPlay:
    """One entry from this round's action stack, redacted for an observer
    who isn't `bandit_name`: the card *type* is only known if it was
    played face-up (i.e. not a Tunnel turn), and the target is never
    known before it resolves."""
    bandit_name: str
    turn_num: int
    card_type: Optional[CardType]  # None if hidden (Tunnel turn)


@dataclass(frozen=True)
class Observation:
    """Everything one bandit is allowed to base a decision on."""
    self_name: str
    self_hand: List[Card]
    self_loot: Dict[LootType, int]
    cars: List[PublicCar]
    marshal_car_id: int
    bandits: Dict[str, PublicBandit]
    round_index: int
    turn: Turn
    plays_seen_this_round: List[SeenPlay]
    gunslinger: Optional[str]

    def car(self, car_id: int) -> Optional[PublicCar]:
        return next((c for c in self.cars if c.id == car_id), None)


def build_observation(state: GameState, bandit_name: str, turn: Turn) -> Observation:
    self_cards = state.cards[bandit_name]

    cars = [
        PublicCar(
            id=car.id,
            is_locomotive=car.is_locomotive,
            loot_inside=dict(Counter(loot.kind for loot in car.loot_inside)),
            loot_roof=dict(Counter(loot.kind for loot in car.loot_roof))
        )
        for car in state.train.cars
    ]

    bandits = {}
    for name, b in state.bandits.items():
        pc = state.cards[name]
        bandits[name] = PublicBandit(
            name=name,
            current_car_id=b.current_car_id,
            is_on_roof=b.is_on_roof,
            carried_loot=dict(Counter(loot.kind for loot in b.loot)),
            bullets_remaining=b.bullets_remaining,
            hand_size=len(pc.hand),
            deck_size=len(pc.deck),
            discard_size=len(pc.discard_pile),
        )

    plays_seen = [
        SeenPlay(
            bandit_name=entry.action.bandit_name,
            turn_num=entry.turn.turn_num,
            card_type=entry.action.card.type if entry.turn.turn_type != TurnType.TUNNEL else None,
        )
        for entry in state.round_stack
    ]

    return Observation(
        self_name=bandit_name,
        self_hand=list(self_cards.hand),
        self_loot=dict(Counter(loot.kind for loot in state.bandits[bandit_name].loot)),
        cars=cars,
        marshal_car_id=state.marshal.current_car_id,
        bandits=bandits,
        round_index=state.round_index,
        turn=turn,
        plays_seen_this_round=plays_seen,
        gunslinger=state.gunslinger,
    )

# ----
# Bridge to CELegalActions.py / CERules.py
#
# Those two modules are typed against GameState, but everything they
# actually read to decide legality - bandit position, roof/inside, bullets
# remaining, the Marshal's car, own hand, how many loot pieces sit
# somewhere - is public information that also lives on Observation. Rather
# than editing CELegalActions.py/CERules.py to accept two different input
# types (and risk them reaching for something hidden), this builds a small
# duck-typed facade over Observation that exposes just the attributes/
# methods those modules touch, and hands *that* in where they expect a
# GameState. An agent's own choose_action() still never sees a real
# GameState - only this read-only view built out of its own Observation.
# ----

class _ObservationCar:
    """Stand-in for a TrainCar. Only `loot_at(...)` is used by CERules.py,
    and only via len(), so a kind-only list works exactly like the real
    (kind+value) list would for legality purposes."""

    def __init__(self, public_car: PublicCar):
        self._public_car = public_car

    def loot_at(self, on_roof: bool) -> List[LootType]:
        return self._public_car.loot_roof if on_roof else self._public_car.loot_inside


class _ObservationTrain:
    """Stand-in for Train, built from public car list."""

    def __init__(self, cars: List[PublicCar]):
        self._cars = cars
        self._by_id = {c.id: _ObservationCar(c) for c in cars}

    def get_car(self, car_id: int) -> Optional[_ObservationCar]:
        return self._by_id.get(car_id)
    
    def neighbors(self, car_id: int) -> List[int]:
        result = []
        if car_id - 1 >= 0:
            result.append(car_id - 1)
        if car_id + 1 < len(self._cars):
            result.append(car_id + 1)
        return result

    def roof_line_of_sight(self, car_id: int, direction: int) -> List[int]:
        result = []
        step = 1 if direction >= 0 else -1
        cid = car_id + step
        while 0 <= cid < len(self._cars):
            result.append(cid)
            cid += step
        return result


class _ObservationMarshal:
    def __init__(self, car_id: int):
        self.current_car_id = car_id


class _ObservationCards:
    """Stand-in for PlayerCards - only `.hand` is read, and only for the
    observer's own bandit, which is fully known to them."""

    def __init__(self, hand: List[Card]):
        self.hand = hand


class _ObservationGameView:
    """Duck-type facade over an Observation, matching the subset of
    GameState's interface CELegalActions.py/CERules.py will actullay use."""

    def __init__(self, obs: Observation):
        self.bandits = obs.bandits  # PublicBandit already has .current_car_id,
                                     # .is_on_roof, .bullets_remaining, .name
        self.cards = {obs.self_name: _ObservationCards(obs.self_hand)}
        self.train = _ObservationTrain(obs.cars)
        self.marshal = _ObservationMarshal(obs.marshal_car_id)

    def active_bandit_names(self) -> List[str]:
        return list(self.bandits.keys())

    def bandit_at(self, car_id: int, on_roof: bool) -> List[str]:
        return [
            name for name, b in self.bandits.items()
            if b.current_car_id == car_id and b.is_on_roof == on_roof
        ]


def legal_actions_for_observation(obs: Observation):
    """What CELegalActions.legal_actions_for(state, bandit_name) would
    return, computed from an Observation instead of a GameState. Safe for
    agents to call from choose_action() - the underlying legality checks
    never touch anything Observation doesn't already expose."""
    from engine.CELegalActions import legal_actions_for  # local import: avoids a
                                                           # module-load cycle since
                                                           # CELegalActions imports
                                                           # engine.CEGameState too
    return legal_actions_for(_ObservationGameView(obs), obs.self_name)
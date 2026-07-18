# CETurnResolution.py
"""
Applies a single Action to GameState. This is the "Stealin' phase" logic:
one action in, state mutated (or a no-op + log entry if illegal), nothing
returned.
"""

from engine import CERules
from engine.CEActions import Action, ActionType
from engine.CEGameState import GameState


def resolve_action(state: GameState, action: Action) -> None:
    bandit =  state.bandits.get(action.bandit_name)
    if bandit is None:
        return
    
    handler = _HANDLERS.get(action.type)
    if handler is None:
        state.log.append(f"{action.bandit_name}: no handler for {action.type}")
        return
    handler(state, action)


def _resolve_move(state: GameState, action: Action) -> None:
    bandit = state.bandits[action.bandit_name]
    if not CERules.can_move(state, action.bandit_name, action.target_car):
        state.log.append(f"{bandit.name}: MOVE to car {action.target_car} was not legal - skipped")
        return
    bandit.move(action.target_car)
    state.log.append(f"{bandit.name}: moved to car {bandit.current_car_id}")


def _resolve_climb(state: GameState, action: Action) -> None:
    bandit = state.bandits[action.bandit_name]
    if not CERules.can_climb(state, action.bandit_name):
        return
    bandit.climb()
    where = "the roof" if bandit.is_on_roof else "inside"
    state.log.append(f"{bandit.name}: climbed to {where} of car {bandit.current_car_id}")


def _resolve_loot(state: GameState, action: Action) -> None:
    bandit = state.bandits[action.bandit_name]
    if not CERules.can_loot(state, action.bandit_name):
        state.log.append(f"{bandit.name}: nothing to loot here - skipped")
        return
    car = state.train.get_car(bandit.current_car_id)
    pool = car.loot_at(bandit.is_on_roof)
    item = pool.pop()  # in the physical game you can only see loot backs, so "any" is fine
    bandit.add_loot(item)
    state.log.append(f"{bandit.name}: looted {item} from car {car.id}")


def _resolve_punch(state: GameState, action: Action) -> None:
    attacker = state.bandits[action.bandit_name]
    if not CERules.can_punch(state, action.bandit_name, action.target_bandit):
        state.log.append(f"{attacker.name}: PUNCH on {action.target_bandit} was not legal - skipped")
        return
    victim = state.bandits[action.target_bandit]

    neighbors = state.train.neighbors(victim.current_car_id)
    knockback_car = None
    if action.target_car in neighbors:
        knockback_car = action.target_car
    elif neighbors:
        knockback_car = neighbors[0]  # default direction if none/invalid specified

    if victim.loot:
        # Real rules let the puncher choose which item is dropped; we
        # simplify to "the last item picked up" until targeting is added
        # TODO: Add targeting logic
        dropped = victim.drop_loot(len(victim.loot) - 1)
        landing_car = state.train.get_car(knockback_car) if knockback_car is not None else state.train.get_car(victim.current_car_id)
        landing_car.add_loot(dropped, victim.is_on_roof)

    if knockback_car is not None:
        victim.move(knockback_car)

    state.log.append(f"{attacker.name}: punched {victim.name} into car {victim.current_car_id}")


def _resolve_shoot(state: GameState, action: Action) -> None:
    shooter = state.bandits[action.bandit_name]
    if not CERules.can_shoot(state, action.bandit_name, action.target_bandit):
        state.log.append(f"{shooter.name}: SHOOT on {action.target_bandit} was not legal - skipped")
        return
    victim = state.bandits[action.target_bandit]

    shooter.bullets_remaining -= 1
    state.cards[victim.name].add_bullet_card()
    state.log.append(f"{shooter.name}: shot {victim.name}")

    if shooter.bullets_remaining == 0 and state.gunslinger is None:
        state.gunslinger = shooter.name
        state.log.append(f"{shooter.name} fired their last bullet - Gunslinger bonus locked in!")


def _resolve_marshal(state: GameState, action: Action) -> None:
    direction = action.direction if action.direction in (-1, 1) else 1
    if not CERules.can_move_marshal(state, action.bandit_name, direction):
        state.log.append(f"{action.bandit_name}: MARSHAL move ({direction:+d}) was not legal - skipped")
        return

    state.marshal.move(state.marshal.current_car_id + direction)
    state.log.append(f"{action.bandit_name}: moved the Marshal to car {state.marshal.current_car_id}")

    # The Marshal fires on everyone caught INSIDE his new car (not on the roof),
    # each takes a bullet card and is forced up onto the roof.
    caught = state.bandit_at(state.marshal.current_car_id, on_roof=False)
    for name in caught:
        victim = state.bandits[name]
        state.cards[name].add_bullet_card()
        victim.climb()  # forced up to the roof
        state.log.append(f"Marshal shot {name} - fled to the roof of car {victim.current_car_id}")


_HANDLERS = {
    ActionType.MOVE: _resolve_move,
    ActionType.CLIMB: _resolve_climb,
    ActionType.LOOT: _resolve_loot,
    ActionType.PUNCH: _resolve_punch,
    ActionType.SHOOT: _resolve_shoot,
    ActionType.MARSHAL: _resolve_marshal,
}
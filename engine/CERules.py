# CERules.py
"""
Legality checks. Every function checks if an action is allow and
never mutates state. CETurnResolution.py calls these before applying
an action, and skips the action rather than raising.
"""

from engine.CEGameState import GameState


def bandit_exists(state: GameState, name: str) -> bool:
    b = state.bandits.get(name)
    return b is not None


def can_move(state: GameState, bandit_name: str, target_car: int) -> bool:
    b = state.bandits[bandit_name]
    return target_car in state.train.neighbors(b.current_car_id)


def can_climb(state: GameState, bandit_name: str) -> bool:
    # Always legal for the bandit's own car - climbing just flips
    # inside/roof for the car you're already in.
    return bandit_name in state.bandits


def can_loot(state: GameState, bandit_name: str) -> bool:
    b = state.bandits[bandit_name]
    car = state.train.get_car(b.current_car_id)
    if car is None:
        return False
    return len(car.loot_at(b.is_on_roof)) > 0


def can_punch(state: GameState, bandit_name: str, target_bandit: str) -> bool:
    if target_bandit not in state.bandits:
        return False
    attacker = state.bandits[bandit_name]
    victim = state.bandits[target_bandit]
    if victim.name == attacker.name:
        return False
    # Must be in the same car, same level (both inside or both on roof)
    return attacker.current_car_id == victim.current_car_id and attacker.is_on_roof == victim.is_on_roof


def _roof_shot_is_clear(state: GameState, shooter_car: int, target_car: int) -> bool:
    """Roof shots travel in a straight line and are blocked by any bandit
    standing on the roof of a car in between (not counting the target)."""
    direction = 1 if target_car > shooter_car else -1
    for cid in state.train.roof_line_of_sight(shooter_car, direction):
        if cid == target_car:
            return True
        if state.bandit_at(cid, on_roof=True):
            return False  # someone's in the way
    return False


def can_shoot(state: GameState, bandit_name: str, target_bandit: str) -> bool:
    if target_bandit not in state.bandits:
        return False
    shooter = state.bandits[bandit_name]
    victim = state.bandits[target_bandit]
    if victim.name == shooter.name:
        return False
    if shooter.bullets_remaining <= 0:
        return False
    if shooter.current_car_id == victim.current_car_id and shooter.is_on_roof == victim.is_on_roof:
        return False  # same spot - that's a PUNCH, not a SHOOT
    
    if shooter.is_on_roof and victim.is_on_roof:
        return _roof_shot_is_clear(state, shooter.current_car_id, victim.current_car_id)
    
    if not shooter.is_on_roof and not victim.is_on_roof:
        # Throught-the-wall shot: only the adjacent car, no line of sight.
        return victim.current_car_id in state.train.neighbors(shooter.current_car_id)
    

    # TODO: Tuco's ability allows for shots through vertical walls
    return False  # roof-to-inside (or vice versa) shots aren't allowed


def can_move_marshal(state: GameState, bandit_name:str, direction: int) -> bool:
    if direction not in (-1, 1):
        return False
    target = state.marshal.current_car_id + direction
    return state.train.get_car(target) is not None
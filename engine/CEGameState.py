# CEGameState.py
"""
GameState is the one object that holds everything about a game in
progress: the train, the marshal, every bandit, every player's cards,
and where we are in the round/turn structure.

Nothing here decides legality or resolves actions - see CERules.py and
CETurnResolution.py. GameState is just the "save file".
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from models.CETrain import Train
from models.CEPieces import Bandit, BanditType, Marshal
from models.CECards import PlayerCards
from engine.CEGameRounds import GameRounds, StackEntry


@dataclass
class GameState:
    train: Train
    marshal: Marshal
    bandits: Dict[str, Bandit]                              # bandit name -> Bandit
    cards: Dict[str, PlayerCards]                           # bandit name -> PlayerCards
    game_rounds: GameRounds
    round_index: int = 0
    first_player_index: int = 0                             # rotates the base seating order each round
    seating_order: List[str] = field(default_factory=list)  # fixed player order
    log: List[str] = field(default_factory=list)
    gunslinger: Optional[str] = None                        # first bandit to exhaust all 6 bullets
    round_stack: List[StackEntry] = field(default_factory=list)  # this round's plays so far, in play order

    @classmethod
    def new_game(cls, bandit_names: List[str], seed: Optional[int] = None) -> "GameState":
        from models.CEPieces import BASE_BANDITS
        available_types = list(BASE_BANDITS.values())
        if len(bandit_names) > len(available_types):
            raise ValueError("Not enough bandit characters for that many players")
        
        train = Train.build_base_game(num_players=len(bandit_names), seed=seed)
        marshal = Marshal(current_car_id=train.locomotive_id)

        bandits = {}
        cards = {}
        for i, name in enumerate(bandit_names):
            # Odd-numbered seats start in the last car per the physical rules
            # simplified here to alternate start cars along the train.
            start_car = 1 + (i % (len(train.cars) - 1))
            bandits[name] = Bandit(
                name=name,
                bandit_type=available_types[i],
                current_car_id=start_car,
                is_on_roof=False,
            )
            cards[name] = PlayerCards()

        game_rounds = GameRounds.create_for_players(len(bandit_names), seed=seed)

        return cls(
            train=train,
            marshal=marshal,
            bandits=bandits,
            cards=cards,
            game_rounds=game_rounds,
            seating_order=list(bandit_names)
        )
    
    @property
    def current_round(self):
        return self.game_rounds.rounds[self.round_index]
    
    def active_bandit_names(self) -> List[str]:
        return [name for name, b in self.bandits.items()]
    
    def turn_order_for_round(self, reversed_order: bool = False) -> List[str]:
        """Seating order rotated so first_player_index goes first. If
        reveresed_order (a SWITCH turn), everyone after the first player
        goes in the opposite direction around the table."""
        n = len(self.seating_order)
        rotated = [self.seating_order[(self.first_player_index + i) % n] for i in range(n)]
        if not reversed_order:
            return rotated
        return [rotated[0]] + list(reversed(rotated[1:]))

    def is_game_over(self) -> bool:
        if self.round_index >= len(self.game_rounds.rounds):
            return True
        return len(self.active_bandit_names()) <= 1
    
    def bandit_at(self, car_id: int, on_roof: bool) -> List[str]:
        return [name for name, b in self.bandits.items()
                if b.is_at(car_id, on_roof)]
    
    def final_scores(self) -> Dict[str, int]:
        scores = {name: b.total_loot_value() for name, b in self.bandits.items()}
        if self.gunslinger is not None:
            scores[self.gunslinger] += 1000
        return scores

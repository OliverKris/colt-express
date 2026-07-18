import pytest
from engine.CEGameRounds import GameRounds, TurnType

@pytest.fixture
def game_3p():
    return GameRounds.create_for_players(3)

def test_round_count(game_3p):
    """Ensure exactly 6 rounds are generated for 3 players."""
    assert len(game_3p.rounds) == 6

def test_turns_are_generated(game_3p):
    """Ensure every round has turns generated (not empty)."""
    for round_obj in game_3p.rounds:
        assert len(round_obj.turns) > 0
        # Verify the first turn object is valid
        assert round_obj.turns[0].turn_num == 1
        assert isinstance(round_obj.turns[0].turn_type, TurnType)

def test_player_bracket_selection():
    """Verify different player counts result in valid generations."""
    game_6p = GameRounds.create_for_players(6)
    assert len(game_6p.rounds) == 6
    # Ensure it didn't crash for the 5-6 bracket
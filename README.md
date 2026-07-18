# colt-express

A Python engine for the base game of **Colt Express.**

## Layout

```text
models/   pure data: Train/Cars/Loot, Bandit/Marshal, Cards & decks
          (no rules logic - just state + tiny structural helpers)
engine/   rules & orchestration
  CEActions.py         Action/ActionType, Card -> ActionType mapping
  CEGameRounds.py       Round/Turn structure, round-card decks
  CEGameState.py        the single "save file" object
  CERules.py            legality checks only (no mutation)
  CETurnResolution.py   applies one Action to state
  CEGameManager.py      runs full rounds (Schemin' -> Stealin')
ai/       pluggable decision-making (random_bot.py is a smoke-test baseline)
tests/    pytest
```

## Design notes / where models end and engine begins

`models/` objects can mutate themselves (`bandit.move(car_id)`) but never
decide whether a move is *legal* - that's always `engine/CERules.py`.
`engine/CETurnResolution.py` is the only place that checks a rule and then
applies it, which is what makes it possible to unit test "what happens if
I shoot here" in isolation from the round/turn loop.

`engine/CEGameManager.py` doesn't know or care *how* a bandit decides what
to play - it just calls an `ActionChooser` callback. Swap `ai/random_bot.py`
for a real AI without touching the engine.

## Running tests

```bash
pip install -r requirements.txt
pytest
```

## Known gaps / assumptions to revisit

- `models/CETrain.build_base_game` approximates loot placement per car -
  swap in the exact printed loot tables if you want board-accurate setup.
- Character special abilities (Doc's 7th card, Belle's punch-immunity, etc.)
  are not implemented - `BanditType.ability` is a placeholder string.
- Round-card end-of-round effects (Station cards, "Angry Marshal", etc.)
  are not implemented - see `Round.eor_effect` / the log line in
  `CEGameManager.run_round`.
- `GameRounds.create_for_players` samples 5 regular rounds + 1 station
  round (6 total). The official rules use 4 regular + 1 station (5 total) -
  worth double-checking which you intended; the existing test asserts 6.
- Marshal & Prisoners / Horses & Stagecoach expansions are out of scope.

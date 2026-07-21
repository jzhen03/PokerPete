from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations

from pokerpete.engine.cards import Card, Deck
from pokerpete.engine.evaluator import score
from pokerpete.engine.ranges import Combo, Range

# Turn+river (or fewer) run-outs are cheap enough to enumerate exactly rather
# than sample; anything wider (flop or preflop) falls back to Monte Carlo.
EXACT_MISSING_THRESHOLD = 2


@dataclass(frozen=True)
class EquityResult:
    win: float
    tie: float
    lose: float

    @property
    def equity(self) -> float:
        return self.win + self.tie / 2


def _showdown(
    hole_a: Sequence[Card], hole_b: Sequence[Card], board: Sequence[Card]
) -> int:
    score_a = score((*hole_a, *board))
    score_b = score((*hole_b, *board))
    return (score_a > score_b) - (score_a < score_b)


def _missing_count(board: Sequence[Card]) -> int:
    if len(board) > 5:
        raise ValueError("board cannot have more than 5 cards")
    return 5 - len(board)


def hand_vs_hand(
    hole_a: Sequence[Card],
    hole_b: Sequence[Card],
    board: Sequence[Card] = (),
    *,
    iterations: int = 20_000,
    seed: int | None = None,
) -> EquityResult:
    """Equity of one specific hole-card pair against another, given a
    (possibly partial) board. Enumerates exactly when few cards remain to
    come, otherwise runs a seeded Monte Carlo simulation."""
    dead = (*hole_a, *hole_b, *board)
    if len(set(dead)) != len(dead):
        raise ValueError("hole cards and board must not share any cards")

    missing = _missing_count(board)
    remaining = Deck(dead=dead).remaining()

    if missing <= EXACT_MISSING_THRESHOLD:
        win = tie = lose = 0
        total = 0
        for completion in combinations(remaining, missing):
            outcome = _showdown(hole_a, hole_b, (*board, *completion))
            total += 1
            win += outcome > 0
            lose += outcome < 0
            tie += outcome == 0
        return EquityResult(win / total, tie / total, lose / total)

    rng = random.Random(seed)
    win = tie = lose = 0
    for _ in range(iterations):
        completion = rng.sample(remaining, missing)
        outcome = _showdown(hole_a, hole_b, (*board, *completion))
        win += outcome > 0
        lose += outcome < 0
        tie += outcome == 0
    return EquityResult(win / iterations, tie / iterations, lose / iterations)


def _filter_for_board(range_: Range, board: Sequence[Card]) -> list[tuple[Combo, float]]:
    board_set = frozenset(board)
    return [
        (combo, weight)
        for combo, weight in range_.items()
        if weight > 0 and combo.isdisjoint(board_set)
    ]


def range_vs_range(
    range_a: Range,
    range_b: Range,
    board: Sequence[Card] = (),
    *,
    iterations: int = 3_000,
    seed: int | None = None,
) -> EquityResult:
    """Monte Carlo equity of one range against another given a (possibly
    partial) board, accounting for card removal between the two ranges and
    the board. Each iteration draws a weighted combo from each range
    (rejecting card conflicts), then completes the board at random."""
    if len(set(board)) != len(board):
        raise ValueError("board cannot contain duplicate cards")
    missing = _missing_count(board)

    combos_a = _filter_for_board(range_a, board)
    combos_b = _filter_for_board(range_b, board)
    if not combos_a or not combos_b:
        raise ValueError("no combos remain in one of the ranges after removing board cards")
    weights_a = [weight for _, weight in combos_a]

    rng = random.Random(seed)
    max_attempts = iterations * 20  # guard against near-total blocker overlap
    win = tie = lose = 0
    counted = 0
    attempts = 0

    while counted < iterations and attempts < max_attempts:
        attempts += 1
        combo_a, _ = rng.choices(combos_a, weights=weights_a, k=1)[0]

        candidates_b = [(combo, weight) for combo, weight in combos_b if combo.isdisjoint(combo_a)]
        if not candidates_b:
            continue
        weights_b = [weight for _, weight in candidates_b]
        combo_b, _ = rng.choices(candidates_b, weights=weights_b, k=1)[0]

        hole_a, hole_b = tuple(combo_a), tuple(combo_b)
        deck = Deck(dead=(*hole_a, *hole_b, *board))
        completion = deck.draw(missing, rng)

        outcome = _showdown(hole_a, hole_b, (*board, *completion))
        counted += 1
        win += outcome > 0
        lose += outcome < 0
        tie += outcome == 0

    if counted == 0:
        raise ValueError("ranges could not be matched against each other (total blocker conflict)")

    return EquityResult(win / counted, tie / counted, lose / counted)

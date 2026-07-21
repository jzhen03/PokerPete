from __future__ import annotations

from collections.abc import Sequence

import eval7

from pokerpete.engine.cards import Card


def _to_eval7(card: Card) -> eval7.Card:
    return eval7.Card(str(card))


def score(cards: Sequence[Card]) -> int:
    """Evaluate the best 5-card hand out of 5, 6, or 7 cards. Higher is better."""
    if not 5 <= len(cards) <= 7:
        raise ValueError("evaluator requires between 5 and 7 cards")
    return eval7.evaluate([_to_eval7(card) for card in cards])


def hand_type(hand_score: int) -> str:
    return eval7.handtype(hand_score)


def compare(
    hole_a: Sequence[Card], hole_b: Sequence[Card], board: Sequence[Card]
) -> int:
    """Return 1 if a wins, -1 if b wins, 0 on a tie, given a shared board."""
    score_a = score((*hole_a, *board))
    score_b = score((*hole_b, *board))
    return (score_a > score_b) - (score_a < score_b)

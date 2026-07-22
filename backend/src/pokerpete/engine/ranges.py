from __future__ import annotations

from collections.abc import Iterable, Mapping
from functools import lru_cache
from types import MappingProxyType

import eval7

from pokerpete.engine.cards import RANKS, Card

Combo = frozenset[Card]
Range = Mapping[Combo, float]


def _combo_from_eval7(pair: tuple[eval7.Card, eval7.Card]) -> Combo:
    a, b = pair
    return frozenset({Card.from_str(str(a)), Card.from_str(str(b))})


@lru_cache(maxsize=512)
def parse(notation: str) -> Range:
    """Parse standard range notation ("AA-TT, AKs, AQo+, 76s", percentages,
    exact combos, etc.) into a weighted mapping of specific two-card combos.

    Grammar parsing is delegated to eval7.HandRange rather than
    re-implemented, since it already handles the full notation syntax
    correctly; this function just adapts the result into our own Card/Range
    types so the rest of the engine doesn't depend on eval7's data model.
    """
    hand_range = eval7.HandRange(notation)
    combos: dict[Combo, float] = {}
    for pair, weight in hand_range:
        combos[_combo_from_eval7(pair)] = weight
    return MappingProxyType(combos)


def union(a: Range, b: Range) -> Range:
    """Combine two ranges, taking the max weight where a combo appears in both."""
    combos = dict(a)
    for combo, weight in b.items():
        combos[combo] = max(combos.get(combo, 0.0), weight)
    return MappingProxyType(combos)


def intersect(a: Range, b: Range) -> Range:
    """Combos present in both ranges, taking the min weight of the two."""
    combos = {combo: min(weight, b[combo]) for combo, weight in a.items() if combo in b}
    return MappingProxyType(combos)


def remove_blockers(range_: Range, dead: Iterable[Card]) -> Range:
    """Drop any combo that shares a card with `dead` (e.g. the board or a
    known opponent hand)."""
    dead_set = frozenset(dead)
    combos = {
        combo: weight for combo, weight in range_.items() if combo.isdisjoint(dead_set)
    }
    return MappingProxyType(combos)


def scale(range_: Range, factor: float) -> Range:
    """Multiply every combo's weight by `factor`, clamped to [0, 1]."""
    combos = {combo: min(1.0, max(0.0, weight * factor)) for combo, weight in range_.items()}
    return MappingProxyType(combos)


def combo_count(range_: Range) -> float:
    """Total weighted combo count (e.g. AA at full weight contributes 6)."""
    return sum(range_.values())


def hand_class_of(combo: Combo) -> str:
    """Canonical starting-hand notation ('AA', 'AKs', 'AKo') for a combo."""
    high, low = sorted(combo, key=lambda c: c.rank, reverse=True)
    if high.rank == low.rank:
        return RANKS[high.rank] * 2
    suited = "s" if high.suit == low.suit else "o"
    return RANKS[high.rank] + RANKS[low.rank] + suited


def _combos_in_class(hand_class: str) -> int:
    if len(hand_class) == 2:  # pocket pair, e.g. "AA"
        return 6
    return 4 if hand_class[2] == "s" else 12


def class_weights(range_: Range) -> dict[str, float]:
    """Aggregate a combo-level Range into per-hand-class average weights in
    [0, 1] (e.g. 2 of AKs's 4 combos present at full weight -> 0.5), suitable
    for rendering a 13x13 range grid."""
    totals: dict[str, float] = {}
    for combo, weight in range_.items():
        hand_class = hand_class_of(combo)
        totals[hand_class] = totals.get(hand_class, 0.0) + weight
    return {
        hand_class: total / _combos_in_class(hand_class) for hand_class, total in totals.items()
    }

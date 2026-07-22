from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Literal

from pokerpete.engine import ranges
from pokerpete.engine.preflop_equity_matrix import canonical_hand_classes, class_weight
from pokerpete.engine.preflop_solver import solve_push_fold_cached

Action = Literal["shove", "fold"]

_CLASSES = canonical_hand_classes()
_CLASS_WEIGHTS = [class_weight(c) for c in _CLASSES]


@dataclass(frozen=True)
class Spot:
    stack_bb: float
    hero_class: str
    hero_combo: str


@dataclass(frozen=True)
class PushFoldGrade:
    correct: bool
    correct_action: Action
    shove_frequency: float


def _random_spot(
    *, min_stack_bb: int, max_stack_bb: int, rng: random.Random | None
) -> Spot:
    """A random hand (weighted by real combo frequency) at a random
    whole-number stack depth. Whole-number depths keep repeated spots
    landing on the same cached solve, which matters since a single solve
    costs roughly a second (push/fold) to several seconds (the open tree)."""
    rng = rng if rng is not None else random.Random()
    hero_class = rng.choices(_CLASSES, weights=_CLASS_WEIGHTS, k=1)[0]
    combo = rng.choice(list(ranges.parse(hero_class).keys()))
    hero_combo = "".join(str(card) for card in sorted(combo, key=lambda c: (-c.rank, -c.suit)))
    stack_bb = float(rng.randint(min_stack_bb, max_stack_bb))
    return Spot(stack_bb=stack_bb, hero_class=hero_class, hero_combo=hero_combo)


def random_push_fold_spot(
    *,
    min_stack_bb: int = 2,
    max_stack_bb: int = 40,
    rng: random.Random | None = None,
) -> Spot:
    """A random SB shove/fold decision."""
    return _random_spot(min_stack_bb=min_stack_bb, max_stack_bb=max_stack_bb, rng=rng)


def random_tree_spot(
    *,
    min_stack_bb: int = 15,
    max_stack_bb: int = 100,
    rng: random.Random | None = None,
) -> Spot:
    """A random SB fold/open/shove decision at a deeper stack, for the
    open/3bet/shove tree (preflop_tree_solver.py) rather than push/fold."""
    return _random_spot(min_stack_bb=min_stack_bb, max_stack_bb=max_stack_bb, rng=rng)


def grade_push_fold(stack_bb: float, hero_class: str, action: Action) -> PushFoldGrade:
    solution = solve_push_fold_cached(stack_bb)
    shove_frequency = solution.sb_shove_frequency[hero_class]
    correct_action: Action = "shove" if shove_frequency >= 0.5 else "fold"
    return PushFoldGrade(
        correct=action == correct_action,
        correct_action=correct_action,
        shove_frequency=shove_frequency,
    )

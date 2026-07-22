import random

import pytest

from pokerpete.engine.cards import parse_cards
from pokerpete.engine.preflop_equity_matrix import DEFAULT_DATA_PATH, canonical_hand_classes
from pokerpete.engine.ranges import hand_class_of
from pokerpete.engine.trainer import grade_push_fold, random_push_fold_spot, random_tree_spot

requires_real_matrix = pytest.mark.skipif(
    not DEFAULT_DATA_PATH.exists(),
    reason="preflop equity matrix artifact not built; run scripts/build_preflop_equity_matrix.py",
)


def test_random_spot_is_well_formed() -> None:
    spot = random_push_fold_spot(rng=random.Random(0))
    assert spot.hero_class in canonical_hand_classes()
    assert 2 <= spot.stack_bb <= 40
    combo = frozenset(parse_cards(spot.hero_combo))
    assert len(combo) == 2
    assert hand_class_of(combo) == spot.hero_class


def test_random_spot_respects_stack_bounds() -> None:
    spot = random_push_fold_spot(min_stack_bb=10, max_stack_bb=10, rng=random.Random(0))
    assert spot.stack_bb == 10.0


def test_random_spot_is_deterministic_with_seed() -> None:
    a = random_push_fold_spot(rng=random.Random(42))
    b = random_push_fold_spot(rng=random.Random(42))
    assert a == b


@requires_real_matrix
def test_grade_premium_hand_shove_is_correct() -> None:
    grade = grade_push_fold(stack_bb=20, hero_class="AA", action="shove")
    assert grade.correct is True
    assert grade.correct_action == "shove"
    assert grade.shove_frequency > 0.9


@requires_real_matrix
def test_grade_premium_hand_fold_is_incorrect() -> None:
    grade = grade_push_fold(stack_bb=20, hero_class="AA", action="fold")
    assert grade.correct is False
    assert grade.correct_action == "shove"


@requires_real_matrix
def test_grade_worst_hand_deep_stack_fold_is_correct() -> None:
    grade = grade_push_fold(stack_bb=40, hero_class="72o", action="fold")
    assert grade.correct is True
    assert grade.correct_action == "fold"


def test_random_tree_spot_is_well_formed() -> None:
    spot = random_tree_spot(rng=random.Random(0))
    assert spot.hero_class in canonical_hand_classes()
    assert 15 <= spot.stack_bb <= 100
    combo = frozenset(parse_cards(spot.hero_combo))
    assert len(combo) == 2
    assert hand_class_of(combo) == spot.hero_class


def test_random_tree_spot_respects_stack_bounds() -> None:
    spot = random_tree_spot(min_stack_bb=30, max_stack_bb=30, rng=random.Random(0))
    assert spot.stack_bb == 30.0

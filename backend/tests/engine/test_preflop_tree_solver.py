import pytest

from pokerpete.engine.preflop_equity_matrix import (
    DEFAULT_DATA_PATH,
    canonical_hand_classes,
    class_weight,
    load_matrix,
)
from pokerpete.engine.preflop_tree_solver import solve_open_tree

# Same mock matrix shape as test_preflop_solver.py, for the same reason:
# fast, deterministic mechanics checks decoupled from the real 169x169 build.
MOCK_MATRIX = {
    "GOOD": {"GOOD": 0.5, "MID": 0.9, "BAD": 0.99},
    "MID": {"GOOD": 0.1, "MID": 0.5, "BAD": 0.75},
    "BAD": {"GOOD": 0.01, "MID": 0.25, "BAD": 0.5},
}
MOCK_WEIGHTS = {"GOOD": 1 / 3, "MID": 1 / 3, "BAD": 1 / 3}


def _assert_is_distribution(strategy: dict, classes) -> None:
    for c in classes:
        total = sum(strategy[c].values())
        assert total == pytest.approx(1.0), f"{c}: {strategy[c]} sums to {total}"
        assert all(0.0 <= p <= 1.0 for p in strategy[c].values())


def test_every_node_is_a_probability_distribution_per_hand() -> None:
    solution = solve_open_tree(MOCK_MATRIX, stack_bb=20, weights=MOCK_WEIGHTS, iterations=150)
    classes = list(MOCK_WEIGHTS)
    _assert_is_distribution(solution.sb_root, classes)
    _assert_is_distribution(solution.bb_vs_open, classes)
    _assert_is_distribution(solution.sb_vs_3bet, classes)
    _assert_is_distribution(solution.bb_vs_shove, classes)
    _assert_is_distribution(solution.sb_vs_shove_after_open, classes)
    _assert_is_distribution(solution.bb_vs_shove_after_3bet, classes)


def test_mock_matrix_dominant_hand_is_never_folded_at_root() -> None:
    solution = solve_open_tree(MOCK_MATRIX, stack_bb=20, weights=MOCK_WEIGHTS, iterations=150)
    assert solution.sb_root["GOOD"]["fold"] == pytest.approx(0.0, abs=0.05)


def test_mock_matrix_worst_hand_is_mostly_folded_at_root_deep() -> None:
    solution = solve_open_tree(MOCK_MATRIX, stack_bb=20, weights=MOCK_WEIGHTS, iterations=150)
    assert solution.sb_root["BAD"]["fold"] > 0.8


def test_mock_matrix_bet_sizes_are_capped_at_stack() -> None:
    # A 1bb stack can't support a 2.5bb open or a 7.5bb 3bet.
    solution = solve_open_tree(MOCK_MATRIX, stack_bb=1, weights=MOCK_WEIGHTS, iterations=50)
    assert solution.open_size_bb == 1.0
    assert solution.threebet_size_bb == 1.0


def test_mock_matrix_bb_always_calls_or_raises_a_shove_with_the_best_hand() -> None:
    solution = solve_open_tree(MOCK_MATRIX, stack_bb=20, weights=MOCK_WEIGHTS, iterations=150)
    assert solution.bb_vs_shove["GOOD"]["fold"] == pytest.approx(0.0, abs=0.05)


# --- Structural sanity checks against the real 169x169 preflop equity matrix.

requires_real_matrix = pytest.mark.skipif(
    not DEFAULT_DATA_PATH.exists(),
    reason="preflop equity matrix artifact not built; run scripts/build_preflop_equity_matrix.py",
)


@pytest.fixture(scope="module")
def real_matrix() -> dict[str, dict[str, float]]:
    return load_matrix()


@pytest.fixture(scope="module")
def real_weights() -> dict[str, float]:
    return {c: class_weight(c) for c in canonical_hand_classes()}


@requires_real_matrix
def test_real_matrix_premium_hand_opens_or_shoves_always(real_matrix, real_weights) -> None:
    solution = solve_open_tree(real_matrix, stack_bb=40, weights=real_weights, iterations=150)
    assert solution.sb_root["AA"]["fold"] == pytest.approx(0.0, abs=0.1)


@requires_real_matrix
def test_real_matrix_worst_hand_mostly_folds_at_root_deep(real_matrix, real_weights) -> None:
    solution = solve_open_tree(real_matrix, stack_bb=40, weights=real_weights, iterations=150)
    assert solution.sb_root["72o"]["fold"] > 0.85


@requires_real_matrix
def test_real_matrix_bb_3bets_or_calls_premium_hands_facing_an_open(
    real_matrix, real_weights
) -> None:
    solution = solve_open_tree(real_matrix, stack_bb=40, weights=real_weights, iterations=150)
    assert solution.bb_vs_open["AA"]["fold"] == pytest.approx(0.0, abs=0.1)


@requires_real_matrix
def test_real_matrix_open_range_is_wider_than_a_shove_only_range(real_matrix, real_weights) -> None:
    # At a deep stack, opening a wide range and folding out weak hands is
    # available as a cheaper alternative to jamming -- SB should be willing
    # to see an open/fold decision on more hands than it would ever shove.
    solution = solve_open_tree(real_matrix, stack_bb=40, weights=real_weights, iterations=150)
    not_fold = sum(
        real_weights[c] * (1 - solution.sb_root[c]["fold"]) for c in solution.sb_root
    )
    shove_only = sum(real_weights[c] * solution.sb_root[c]["shove"] for c in solution.sb_root)
    assert not_fold > shove_only

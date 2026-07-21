import pytest

from pokerpete.engine.preflop_equity_matrix import (
    DEFAULT_DATA_PATH,
    canonical_hand_classes,
    class_weight,
    load_matrix,
)
from pokerpete.engine.preflop_solver import solve_push_fold

# A tiny synthetic 3-class matrix, decoupled from real poker notation, so the
# fictitious-play mechanics can be checked without paying for the real
# 169x169 matrix build. "GOOD" crushes both other classes, "BAD" loses to
# both, "MID" splits evenly with itself and is a coinflip-ish middle class.
MOCK_MATRIX = {
    "GOOD": {"GOOD": 0.5, "MID": 0.9, "BAD": 0.99},
    "MID": {"GOOD": 0.1, "MID": 0.5, "BAD": 0.75},
    "BAD": {"GOOD": 0.01, "MID": 0.25, "BAD": 0.5},
}
MOCK_WEIGHTS = {"GOOD": 1 / 3, "MID": 1 / 3, "BAD": 1 / 3}


def test_mock_matrix_dominant_hand_always_shoved_and_called() -> None:
    # Fictitious play's running average converges asymptotically, not
    # exactly, at any finite iteration count -- a small residual from early
    # rounds is expected, hence the loose tolerance.
    solution = solve_push_fold(MOCK_MATRIX, stack_bb=20, weights=MOCK_WEIGHTS, iterations=200)
    assert solution.sb_shove_frequency["GOOD"] == pytest.approx(1.0, abs=0.05)
    assert solution.bb_call_frequency["GOOD"] == pytest.approx(1.0, abs=0.05)


def test_mock_matrix_bad_hand_never_shoved_deep() -> None:
    # 20bb is deep enough that jamming a hand which loses to everything
    # (crushed by GOOD, well behind MID) cannot be profitable.
    solution = solve_push_fold(MOCK_MATRIX, stack_bb=20, weights=MOCK_WEIGHTS, iterations=200)
    assert solution.sb_shove_frequency["BAD"] == pytest.approx(0.0, abs=0.05)


def test_mock_matrix_shallow_stack_widens_shoving_range() -> None:
    shallow = solve_push_fold(MOCK_MATRIX, stack_bb=2, weights=MOCK_WEIGHTS, iterations=200)
    deep = solve_push_fold(MOCK_MATRIX, stack_bb=20, weights=MOCK_WEIGHTS, iterations=200)
    shallow_total = sum(shallow.sb_shove_frequency.values())
    deep_total = sum(deep.sb_shove_frequency.values())
    assert shallow_total >= deep_total


def test_solution_range_helpers_respect_threshold() -> None:
    solution = solve_push_fold(MOCK_MATRIX, stack_bb=20, weights=MOCK_WEIGHTS, iterations=200)
    assert "GOOD" in solution.sb_shove_range()
    assert "BAD" not in solution.sb_shove_range()
    assert solution.stack_bb == 20
    assert solution.iterations == 200


# --- Structural sanity checks against the real 169x169 preflop equity matrix.
#
# There's no bundled reference dataset to replicate published push/fold
# charts number-for-number, so these instead check the well-established
# qualitative hallmarks of a correct push/fold equilibrium: premium hands are
# always shoved/called, the worst hand is only shoved when stacks are very
# shallow, and the shoving range narrows as the stack deepens.

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
def test_real_matrix_premium_hand_always_shoved_and_called(real_matrix, real_weights) -> None:
    solution = solve_push_fold(real_matrix, stack_bb=20, weights=real_weights, iterations=150)
    assert solution.sb_shove_frequency["AA"] == pytest.approx(1.0, abs=0.1)
    assert solution.bb_call_frequency["AA"] == pytest.approx(1.0, abs=0.1)


@requires_real_matrix
def test_real_matrix_worst_hand_never_shoved(real_matrix, real_weights) -> None:
    # 72o is folded at *every* depth, including very shallow stacks: at 2bb
    # the pot odds are so good that BB's Nash calling range is nearly 100%,
    # which erases SB's fold-equity edge and leaves 72o's ~34% raw equity
    # short of what's needed to beat folding. This is a real, well-known
    # property of the Nash push/fold game, not just a "shove wide when
    # shallow" heuristic -- the aggregate range is very wide at 2bb (see
    # test_real_matrix_shove_range_is_very_wide_when_shallow below), but it
    # still excludes the handful of very worst hands.
    for stack in (2, 5, 10, 20, 40):
        solution = solve_push_fold(
            real_matrix, stack_bb=stack, weights=real_weights, iterations=150
        )
        assert solution.sb_shove_frequency["72o"] < 0.15


@requires_real_matrix
def test_real_matrix_shove_range_is_very_wide_when_shallow(real_matrix, real_weights) -> None:
    solution = solve_push_fold(real_matrix, stack_bb=2, weights=real_weights, iterations=300)
    total_shove = sum(real_weights[c] * f for c, f in solution.sb_shove_frequency.items())
    assert total_shove > 0.85


@requires_real_matrix
def test_real_matrix_marginal_hand_shoved_shallow_folded_deep(real_matrix, real_weights) -> None:
    # A2o: enough equity to profitably jam a wide, shallow-stack calling
    # range, but not enough to justify committing a much deeper stack once
    # BB's Nash calling range tightens to genuinely strong hands.
    shallow = solve_push_fold(real_matrix, stack_bb=5, weights=real_weights, iterations=300)
    deep = solve_push_fold(real_matrix, stack_bb=40, weights=real_weights, iterations=300)
    assert shallow.sb_shove_frequency["A2o"] > 0.8
    assert deep.sb_shove_frequency["A2o"] < 0.2


@requires_real_matrix
def test_real_matrix_shove_range_narrows_as_stack_deepens(real_matrix, real_weights) -> None:
    stacks = [2, 5, 10, 20, 40]
    totals = [
        sum(
            real_weights[c] * f
            for c, f in solve_push_fold(
                real_matrix, stack_bb=stack, weights=real_weights, iterations=150
            ).sb_shove_frequency.items()
        )
        for stack in stacks
    ]
    # Allow a little noise between adjacent depths, but the overall trend
    # across the full range must be a clear, monotonic-ish narrowing.
    assert totals[0] > totals[-1] + 0.2
    assert all(a >= b - 0.05 for a, b in zip(totals, totals[1:], strict=False))

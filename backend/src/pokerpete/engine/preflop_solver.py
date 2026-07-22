from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from pokerpete.engine.preflop_equity_matrix import class_weight, default_matrix

# Both players have already posted their blind; folding forfeits only that
# blind, which is what these EVs are measured against.
FOLD_EV_SB = -0.5
FOLD_EV_BB = -1.0


@dataclass(frozen=True)
class PushFoldSolution:
    stack_bb: float
    sb_shove_frequency: Mapping[str, float]
    bb_call_frequency: Mapping[str, float]
    iterations: int

    def sb_shove_range(self, threshold: float = 0.5) -> set[str]:
        return {c for c, f in self.sb_shove_frequency.items() if f >= threshold}

    def bb_call_range(self, threshold: float = 0.5) -> set[str]:
        return {c for c, f in self.bb_call_frequency.items() if f >= threshold}


def _sb_best_response(
    matrix: Mapping[str, Mapping[str, float]],
    bb_call_freq: Mapping[str, float],
    stack_bb: float,
    weights: Mapping[str, float],
) -> dict[str, float]:
    """For each SB hand, 1.0 if shoving beats folding against BB's calling
    frequencies, else 0.0."""
    br: dict[str, float] = {}
    for hand_i, row in matrix.items():
        ev_shove = 0.0
        for hand_j, weight_j in weights.items():
            call = bb_call_freq[hand_j]
            eq = row[hand_j]
            ev_shove += weight_j * ((1 - call) * 1.0 + call * stack_bb * (2 * eq - 1))
        br[hand_i] = 1.0 if ev_shove > FOLD_EV_SB else 0.0
    return br


def _bb_best_response(
    matrix: Mapping[str, Mapping[str, float]],
    sb_shove_freq: Mapping[str, float],
    stack_bb: float,
    weights: Mapping[str, float],
) -> dict[str, float]:
    """For each BB hand, 1.0 if calling a shove beats folding against SB's
    (weight-normalized) shoving frequencies, else 0.0."""
    shove_mass = sum(weights[h] * sb_shove_freq[h] for h in sb_shove_freq)
    if shove_mass <= 0:
        return dict.fromkeys(weights, 0.0)

    br: dict[str, float] = {}
    for hand_j in weights:
        ev_call = 0.0
        for hand_i, weight_i in weights.items():
            p_i = weight_i * sb_shove_freq[hand_i] / shove_mass
            eq = matrix[hand_i][hand_j]
            ev_call += p_i * stack_bb * (1 - 2 * eq)
        br[hand_j] = 1.0 if ev_call > FOLD_EV_BB else 0.0
    return br


def solve_push_fold(
    matrix: Mapping[str, Mapping[str, float]],
    stack_bb: float,
    *,
    weights: Mapping[str, float] | None = None,
    iterations: int = 300,
) -> PushFoldSolution:
    """Nash equilibrium of the heads-up shove/fold game at this stack depth,
    via fictitious play: each side repeatedly best-responds to the running
    time-average of the other's strategy from the previous round. This is a
    small fixed-point game (not a CFR problem) and converges in well under
    `iterations` rounds for realistic matrices.

    `weights` lets callers supply a synthetic hand-class -> probability
    mapping (e.g. for tests against a small mocked matrix); it defaults to
    real 169-hand-class combo-count weights, which requires `matrix`'s keys
    to be valid poker hand notations.
    """
    classes = tuple(matrix.keys())
    resolved_weights = weights if weights is not None else {c: class_weight(c) for c in classes}

    avg_sb: dict[str, float] = dict.fromkeys(classes, 0.0)
    avg_bb: dict[str, float] = dict.fromkeys(classes, 0.0)

    for t in range(1, iterations + 1):
        br_sb = _sb_best_response(matrix, avg_bb, stack_bb, resolved_weights)
        br_bb = _bb_best_response(matrix, avg_sb, stack_bb, resolved_weights)
        for c in classes:
            avg_sb[c] += (br_sb[c] - avg_sb[c]) / t
            avg_bb[c] += (br_bb[c] - avg_bb[c]) / t

    return PushFoldSolution(
        stack_bb=stack_bb,
        sb_shove_frequency=avg_sb,
        bb_call_frequency=avg_bb,
        iterations=iterations,
    )


@lru_cache(maxsize=512)
def solve_push_fold_cached(stack_bb: float, iterations: int = 300) -> PushFoldSolution:
    """Memoized convenience wrapper around `solve_push_fold` using the
    committed equity matrix artifact. A single solve takes roughly a second,
    so callers issuing repeated requests at the same stack depth (the API
    layer, the trainer) should go through this rather than `solve_push_fold`
    directly."""
    return solve_push_fold(default_matrix(), stack_bb, iterations=iterations)

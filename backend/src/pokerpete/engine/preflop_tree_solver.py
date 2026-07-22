"""Nash equilibrium solver for the heads-up open/3bet/shove preflop tree at
deeper stacks, where shove/fold alone (preflop_solver.py) is too narrow.

Tree (SB acts first; every size is capped at the effective stack):

  SB root: fold / open (to `open_size`) / shove (to stack)
    -> BB vs shove: fold / call                       [showdown at stack]
    -> BB vs open: fold / call / 3bet (to 3x open) / shove (to stack)
         -> call: showdown on the open-sized pot
         -> 3bet -> SB vs 3bet: fold / call / shove
              -> call: showdown on the 3bet-sized pot
              -> shove -> BB vs shove-after-3bet: fold / call [showdown at stack]
         -> shove -> SB vs shove-after-open: fold / call     [showdown at stack]

Every non-fold, non-all-in-showdown terminal (i.e. every plain call) is
scored at 100% equity realization: an immediate showdown on the pot as it
stands, with any stack behind it untouched. This is a deliberate,
documented simplification -- we are not modeling postflop play, so a call
carries no implied odds or postflop skill edge (see docs/architecture.md's
risk section).

CONFIRMED CONSEQUENCE, not a bug (verified by hand-checking terminal EVs
against direct equity-vs-range calculations): this model's equilibria lean
heavily toward maximal aggression once ahead. With no postflop skill or
implied-odds value on the table, committing more money when you have an
edge is simply better, with nothing to weigh against it -- so BB's response
to an open is very often a shove rather than a smaller 3bet, and SB's
response to a 3bet is very often a shove rather than a flat call, at almost
any stack depth this tree is used for. Real HU cash players size down and
play more postflop pots than this model will ever recommend. Treat this
solver's output as "correct for a no-postflop simplification," not as a
faithful stand-in for real GTO strategy at these stacks -- callers (the API
layer, the frontend) must surface that caveat, not just this module.

Solved via the same generalized fictitious play as preflop_solver.py's
push/fold game: each side repeatedly best-responds, via backward induction
over this tree, to the running time-average of the other's full strategy
from the previous round. This is a different (larger) game than push/fold
but not a different algorithm -- CFR isn't needed for a game this small,
and reusing fictitious play keeps the two solvers consistent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pokerpete.engine.preflop_equity_matrix import class_weight

OPEN_SIZE_BB = 2.5
THREEBET_MULTIPLIER = 3.0

# Bump whenever the tree structure, sizing, or equity-realization assumption
# changes, so a cached solver_results row can never silently go stale.
SOLVER_VERSION = "open-3bet-shove-v1"

MODEL_CAVEAT = (
    "This preflop-only model doesn't account for postflop play, so it tends to "
    "favor maximally-sized bets whenever a hand has an edge -- real players size "
    "down and play more pots after the flop than this solver will ever recommend. "
    "Treat it as a fold-equity and range-construction study aid, not real GTO "
    "strategy for these stacks."
)

Strategy = Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class TreeSolution:
    stack_bb: float
    open_size_bb: float
    threebet_size_bb: float
    sb_root: Strategy
    bb_vs_open: Strategy
    sb_vs_3bet: Strategy
    bb_vs_shove: Strategy
    sb_vs_shove_after_open: Strategy
    bb_vs_shove_after_3bet: Strategy
    iterations: int


def _sb_ev(size: float, eq: float) -> float:
    """SB's net EV putting `size` in and going to showdown at equity `eq`."""
    return size * (2 * eq - 1)


def _bb_ev(size: float, eq: float) -> float:
    """BB's net EV putting `size` in and going to showdown, `eq` being SB's equity."""
    return size * (1 - 2 * eq)


def _pure_best(evs: Mapping[str, float]) -> tuple[dict[str, float], float]:
    best_action = max(evs, key=lambda a: evs[a])
    policy = {a: (1.0 if a == best_action else 0.0) for a in evs}
    return policy, evs[best_action]


def _belief(weights: Mapping[str, float], reach: Mapping[str, float]) -> dict[str, float] | None:
    """Normalize weight(h) * reach(h) into a distribution over hand classes
    conditioned on reaching this node; None if the node is never reached."""
    raw = {h: weights[h] * reach.get(h, 0.0) for h in weights}
    total = sum(raw.values())
    if total <= 0:
        return None
    return {h: v / total for h, v in raw.items()}


def _sb_best_response(
    matrix: Strategy,
    weights: Mapping[str, float],
    stack_bb: float,
    open_size: float,
    threebet_size: float,
    bb_vs_shove: Strategy,
    bb_vs_open: Strategy,
    bb_vs_shove_after_3bet: Strategy,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """SB's full best response (root, vs-3bet, vs-shove-after-open) to BB's
    fixed strategy, via backward induction: the two SB-owned leaf nodes are
    computed first, then their resulting EVs feed the root's "open" branch."""
    sb_vs_shove_after_open: dict[str, dict[str, float]] = {}
    sb_vs_shove_after_open_value: dict[str, float] = {}
    for i in weights:
        ev_fold = -open_size
        ev_call = sum(weights[j] * _sb_ev(stack_bb, matrix[i][j]) for j in weights)
        policy, value = _pure_best({"fold": ev_fold, "call": ev_call})
        sb_vs_shove_after_open[i] = policy
        sb_vs_shove_after_open_value[i] = value

    sb_vs_3bet: dict[str, dict[str, float]] = {}
    sb_vs_3bet_value: dict[str, float] = {}
    for i in weights:
        ev_fold = -open_size
        ev_call = sum(weights[j] * _sb_ev(threebet_size, matrix[i][j]) for j in weights)
        ev_shove = sum(
            weights[j]
            * (
                bb_vs_shove_after_3bet[j]["fold"] * threebet_size
                + bb_vs_shove_after_3bet[j]["call"] * _sb_ev(stack_bb, matrix[i][j])
            )
            for j in weights
        )
        policy, value = _pure_best({"fold": ev_fold, "call": ev_call, "shove": ev_shove})
        sb_vs_3bet[i] = policy
        sb_vs_3bet_value[i] = value

    sb_root: dict[str, dict[str, float]] = {}
    for i in weights:
        ev_fold = -0.5
        ev_shove = sum(
            weights[j]
            * (
                bb_vs_shove[j]["fold"] * 1.0
                + bb_vs_shove[j]["call"] * _sb_ev(stack_bb, matrix[i][j])
            )
            for j in weights
        )
        ev_open = sum(
            weights[j]
            * (
                bb_vs_open[j]["fold"] * 1.0
                + bb_vs_open[j]["call"] * _sb_ev(open_size, matrix[i][j])
                + bb_vs_open[j]["threebet"] * sb_vs_3bet_value[i]
                + bb_vs_open[j]["shove"] * sb_vs_shove_after_open_value[i]
            )
            for j in weights
        )
        policy, _ = _pure_best({"fold": ev_fold, "open": ev_open, "shove": ev_shove})
        sb_root[i] = policy

    return sb_root, sb_vs_3bet, sb_vs_shove_after_open


def _bb_best_response(
    matrix: Strategy,
    weights: Mapping[str, float],
    stack_bb: float,
    open_size: float,
    threebet_size: float,
    sb_root: Strategy,
    sb_vs_shove_after_open: Strategy,
    sb_vs_3bet: Strategy,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """BB's full best response (vs-shove, vs-open, vs-shove-after-3bet) to
    SB's fixed strategy, via backward induction over BB's own three nodes."""
    belief_shove = _belief(weights, {i: sb_root[i]["shove"] for i in weights})
    bb_vs_shove: dict[str, dict[str, float]] = {}
    for j in weights:
        if belief_shove is None:
            bb_vs_shove[j] = {"fold": 1.0, "call": 0.0}
            continue
        ev_fold = -1.0
        ev_call = sum(belief_shove[i] * _bb_ev(stack_bb, matrix[i][j]) for i in belief_shove)
        policy, _ = _pure_best({"fold": ev_fold, "call": ev_call})
        bb_vs_shove[j] = policy

    belief_3bet_shove = _belief(
        weights, {i: sb_root[i]["open"] * sb_vs_3bet[i]["shove"] for i in weights}
    )
    bb_vs_shove_after_3bet: dict[str, dict[str, float]] = {}
    bb_vs_shove_after_3bet_value: dict[str, float] = {}
    for j in weights:
        if belief_3bet_shove is None:
            bb_vs_shove_after_3bet[j] = {"fold": 1.0, "call": 0.0}
            bb_vs_shove_after_3bet_value[j] = -threebet_size
            continue
        ev_fold = -threebet_size
        ev_call = sum(
            belief_3bet_shove[i] * _bb_ev(stack_bb, matrix[i][j]) for i in belief_3bet_shove
        )
        policy, value = _pure_best({"fold": ev_fold, "call": ev_call})
        bb_vs_shove_after_3bet[j] = policy
        bb_vs_shove_after_3bet_value[j] = value

    belief_open = _belief(weights, {i: sb_root[i]["open"] for i in weights})
    bb_vs_open: dict[str, dict[str, float]] = {}
    for j in weights:
        if belief_open is None:
            bb_vs_open[j] = {"fold": 1.0, "call": 0.0, "threebet": 0.0, "shove": 0.0}
            continue
        ev_fold = -1.0
        ev_call = sum(belief_open[i] * _bb_ev(open_size, matrix[i][j]) for i in belief_open)
        ev_shove = sum(
            belief_open[i]
            * (
                sb_vs_shove_after_open[i]["fold"] * open_size
                + sb_vs_shove_after_open[i]["call"] * _bb_ev(stack_bb, matrix[i][j])
            )
            for i in belief_open
        )
        ev_threebet = sum(
            belief_open[i]
            * (
                sb_vs_3bet[i]["fold"] * open_size
                + sb_vs_3bet[i]["call"] * _bb_ev(threebet_size, matrix[i][j])
                + sb_vs_3bet[i]["shove"] * bb_vs_shove_after_3bet_value[j]
            )
            for i in belief_open
        )
        policy, _ = _pure_best(
            {"fold": ev_fold, "call": ev_call, "threebet": ev_threebet, "shove": ev_shove}
        )
        bb_vs_open[j] = policy

    return bb_vs_shove, bb_vs_open, bb_vs_shove_after_3bet


def solve_open_tree(
    matrix: Strategy,
    stack_bb: float,
    *,
    weights: Mapping[str, float] | None = None,
    open_size_bb: float = OPEN_SIZE_BB,
    iterations: int = 300,
) -> TreeSolution:
    classes = tuple(matrix.keys())
    resolved_weights = weights if weights is not None else {c: class_weight(c) for c in classes}
    open_size = min(open_size_bb, stack_bb)
    threebet_size = min(open_size * THREEBET_MULTIPLIER, stack_bb)

    avg_sb_root = {c: {"fold": 0.0, "open": 0.0, "shove": 0.0} for c in classes}
    avg_sb_vs_3bet = {c: {"fold": 0.0, "call": 0.0, "shove": 0.0} for c in classes}
    avg_sb_vs_shove_after_open = {c: {"fold": 0.0, "call": 0.0} for c in classes}
    avg_bb_vs_open = {c: {"fold": 0.0, "call": 0.0, "threebet": 0.0, "shove": 0.0} for c in classes}
    avg_bb_vs_shove = {c: {"fold": 0.0, "call": 0.0} for c in classes}
    avg_bb_vs_shove_after_3bet = {c: {"fold": 0.0, "call": 0.0} for c in classes}

    def _blend(
        avg: dict[str, dict[str, float]], new: Mapping[str, Mapping[str, float]], t: int
    ) -> None:
        for c in avg:
            for a in avg[c]:
                avg[c][a] += (new[c][a] - avg[c][a]) / t

    for t in range(1, iterations + 1):
        br_sb_root, br_sb_vs_3bet, br_sb_vs_shove_after_open = _sb_best_response(
            matrix,
            resolved_weights,
            stack_bb,
            open_size,
            threebet_size,
            avg_bb_vs_shove,
            avg_bb_vs_open,
            avg_bb_vs_shove_after_3bet,
        )
        br_bb_vs_shove, br_bb_vs_open, br_bb_vs_shove_after_3bet = _bb_best_response(
            matrix,
            resolved_weights,
            stack_bb,
            open_size,
            threebet_size,
            avg_sb_root,
            avg_sb_vs_shove_after_open,
            avg_sb_vs_3bet,
        )
        _blend(avg_sb_root, br_sb_root, t)
        _blend(avg_sb_vs_3bet, br_sb_vs_3bet, t)
        _blend(avg_sb_vs_shove_after_open, br_sb_vs_shove_after_open, t)
        _blend(avg_bb_vs_open, br_bb_vs_open, t)
        _blend(avg_bb_vs_shove, br_bb_vs_shove, t)
        _blend(avg_bb_vs_shove_after_3bet, br_bb_vs_shove_after_3bet, t)

    return TreeSolution(
        stack_bb=stack_bb,
        open_size_bb=open_size,
        threebet_size_bb=threebet_size,
        sb_root=avg_sb_root,
        bb_vs_open=avg_bb_vs_open,
        sb_vs_3bet=avg_sb_vs_3bet,
        bb_vs_shove=avg_bb_vs_shove,
        sb_vs_shove_after_open=avg_sb_vs_shove_after_open,
        bb_vs_shove_after_3bet=avg_bb_vs_shove_after_3bet,
        iterations=iterations,
    )

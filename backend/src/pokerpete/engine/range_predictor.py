"""Range Predictor: a heuristic (not solved) range-narrowing pipeline.

Position -> Player Type -> Bet Sizing, each a pure filter over a
hand-class-keyed WeightedRange (same shape as ranges.class_weights()'s output
and RangeGrid's props). Each filter reports what it changed via a RangeDiff
so a future layer-stepper/Explain UI can describe construction without
re-deriving it -- built now even though that UI is deferred.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Literal

from pokerpete.engine import ranges
from pokerpete.engine.cards import RANKS
from pokerpete.engine.data.bet_sizing_skew import BET_SIZING_SKEW, NON_SIZING_ACTIONS
from pokerpete.engine.data.player_type_modifiers import PLAYER_TYPE_MODIFIERS
from pokerpete.engine.data.range_predictor_baselines import baseline_range
from pokerpete.engine.preflop_equity_matrix import canonical_hand_classes

WeightedRange = dict[str, float]
StageName = Literal["position", "player_type", "bet_sizing"]


@dataclass(frozen=True)
class RangeDiff:
    added: dict[str, float]
    removed: dict[str, float]
    reweighted: dict[str, tuple[float, float]]


@dataclass(frozen=True)
class FilterResult:
    range: WeightedRange
    diff: RangeDiff


def diff_ranges(before: WeightedRange, after: WeightedRange) -> RangeDiff:
    """Pure comparison of two WeightedRanges into added/removed/reweighted
    hand-classes -- used by every filter below to report what it changed."""
    added: dict[str, float] = {}
    removed: dict[str, float] = {}
    reweighted: dict[str, tuple[float, float]] = {}
    for hand_class in set(before) | set(after):
        b, a = before.get(hand_class, 0.0), after.get(hand_class, 0.0)
        if b <= 0 and a > 0:
            added[hand_class] = a
        elif b > 0 and a <= 0:
            removed[hand_class] = b
        elif b > 0 and a > 0 and abs(a - b) > 1e-9:
            reweighted[hand_class] = (b, a)
    return RangeDiff(added, removed, reweighted)


def _combos(hand_class: str) -> float:
    return ranges.combo_count(ranges.parse(hand_class))


def _weighted_combo_count(weighted_range: WeightedRange) -> float:
    return sum(w * _combos(c) for c, w in weighted_range.items() if w > 0)


_HIGH_CARD_SCORE: dict[str, float] = {
    "A": 10.0,
    "K": 8.0,
    "Q": 7.0,
    "J": 6.0,
    "T": 5.0,
    "9": 4.5,
    "8": 4.0,
    "7": 3.5,
    "6": 3.0,
    "5": 2.5,
    "4": 2.0,
    "3": 1.5,
    "2": 1.0,
}


def _strength_score(hand_class: str) -> float:
    """Deterministic hand-strength approximation (a simplified Chen Formula)
    used only to order/partition the 169-class universe for this heuristic
    pipeline -- not a substitute for the (optional, offline-built) equity
    matrix used elsewhere in the engine."""
    if len(hand_class) == 2:  # pocket pair, e.g. "AA"
        return max(_HIGH_CARD_SCORE[hand_class[0]] * 2, 5.0)

    high, low, suited = hand_class[0], hand_class[1], hand_class[2] == "s"
    score = _HIGH_CARD_SCORE[high]
    if suited:
        score += 2.0

    gap = RANKS.index(high) - RANKS.index(low) - 1
    score -= {0: 0.0, 1: 1.0, 2: 2.0, 3: 4.0}.get(gap, 5.0)
    if gap <= 1 and RANKS.index(high) < RANKS.index("Q"):
        score += 1.0
    return score


def _is_speculative(hand_class: str) -> bool:
    """Small pairs, suited connectors/one-gappers below broadway, and suited
    aces -- the hands that read as equity/bluff candidates rather than
    made-hand value. Suited broadway combos (KQs, QJs, ...) are excluded even
    though they're gap<=1 -- those play as value, not bluffs."""
    if len(hand_class) == 2:
        return RANKS.index(hand_class[0]) <= RANKS.index("9")

    high, low, suited = hand_class[0], hand_class[1], hand_class[2] == "s"
    if not suited:
        return False
    if high == "A":
        return RANKS.index(low) <= RANKS.index("9")
    gap = RANKS.index(high) - RANKS.index(low) - 1
    return gap <= 1 and RANKS.index(high) < RANKS.index("Q")


def _widen(range_in: WeightedRange, target_count: float, shift: str) -> WeightedRange:
    result = dict(range_in)

    def priority(hand_class: str) -> tuple[int, float]:
        if shift == "polarized":
            return (0 if _is_speculative(hand_class) else 1, -_strength_score(hand_class))
        return (0, -_strength_score(hand_class))

    candidates = sorted(
        (c for c in canonical_hand_classes() if result.get(c, 0.0) < 1.0), key=priority
    )
    total = _weighted_combo_count(result)
    for hand_class in candidates:
        if total >= target_count:
            break
        weight = result.get(hand_class, 0.0)
        class_combos = _combos(hand_class)
        capacity = class_combos * (1.0 - weight)
        needed = target_count - total
        if needed >= capacity:
            result[hand_class] = 1.0
            total += capacity
        else:
            result[hand_class] = weight + needed / class_combos
            total += needed
    return result


def _narrow(range_in: WeightedRange, target_count: float, shift: str) -> WeightedRange:
    result = dict(range_in)
    included = [c for c, w in result.items() if w > 0]
    if not included:
        return result

    if shift == "polarized":
        median_score = statistics.median(_strength_score(c) for c in included)

        def priority(hand_class: str) -> float:
            distance = abs(_strength_score(hand_class) - median_score)
            return distance + (1000.0 if _is_speculative(hand_class) else 0.0)
    else:

        def priority(hand_class: str) -> float:
            return _strength_score(hand_class)

    order = sorted(included, key=priority)
    total = _weighted_combo_count(result)
    for hand_class in order:
        if total <= target_count:
            break
        weight = result[hand_class]
        class_combos = _combos(hand_class)
        have = weight * class_combos
        excess = total - target_count
        if excess >= have:
            result[hand_class] = 0.0
            total -= have
        else:
            result[hand_class] = weight - excess / class_combos
            total -= excess
    return {c: w for c, w in result.items() if w > 1e-9}


def apply_player_type(range_in: WeightedRange, player_type: str) -> FilterResult:
    """Widen/narrow the input range by the player type's width delta, biased
    toward its linear/polarized shape when choosing which hands move."""
    modifier = PLAYER_TYPE_MODIFIERS[player_type]
    if modifier.width_delta_pct == 0:
        return FilterResult(dict(range_in), RangeDiff({}, {}, {}))

    current_count = _weighted_combo_count(range_in)
    target_count = current_count * (1 + modifier.width_delta_pct / 100)

    result = (
        _widen(range_in, target_count, modifier.shift)
        if modifier.width_delta_pct > 0
        else _narrow(range_in, target_count, modifier.shift)
    )
    return FilterResult(result, diff_ranges(range_in, result))


def apply_bet_sizing(
    range_in: WeightedRange,
    action: str,
    sizing_bucket: str | None,
    reliability: int,
    street: str = "preflop",
) -> FilterResult:
    """Blends range_in toward a fully-narrowed target (BET_SIZING_SKEW's
    value/bluff allocation, with everything else -- "filler" -- dropped to
    zero) proportionally to `reliability`: 0 leaves the range untouched
    ("sizing tells you nothing, don't narrow at all"), 100 applies the full
    narrowing ("sizing is fully trustworthy, narrow hard"), and values in
    between blend every hand's weight linearly, producing a softer, more
    blended opacity for low-reliability player types rather than a sharp
    include/exclude cutoff."""
    if action in NON_SIZING_ACTIONS or sizing_bucket is None:
        return FilterResult(dict(range_in), RangeDiff({}, {}, {}))

    skew = BET_SIZING_SKEW[(action, sizing_bucket, street)]
    included = [c for c, w in range_in.items() if w > 0]
    if not included:
        return FilterResult(dict(range_in), RangeDiff({}, {}, {}))

    total_combos = _weighted_combo_count(range_in)

    def allocate(order: list[str], budget: float) -> dict[str, float]:
        """Greedily assign combo-weighted `budget` across `order`, giving
        partial weight to the class that would overshoot so the allocation
        is exact rather than always rounding up to a whole class -- avoids
        overshoot artifacts that would otherwise make filler-share (and
        hence narrowing) non-monotonic across sizing buckets."""
        taken: dict[str, float] = {}
        running = 0.0
        for hand_class in order:
            if running >= budget:
                break
            weight = range_in[hand_class]
            available = weight * _combos(hand_class)
            remaining = budget - running
            if remaining >= available:
                taken[hand_class] = weight
                running += available
            else:
                taken[hand_class] = remaining / _combos(hand_class)
                running += remaining
        return taken

    by_strength = sorted(included, key=lambda c: -_strength_score(c))
    value_alloc = allocate(by_strength, total_combos * skew.value_share)

    remaining_candidates = [c for c in included if c not in value_alloc]
    by_speculative = sorted(
        remaining_candidates, key=lambda c: (0 if _is_speculative(c) else 1, -_strength_score(c))
    )
    bluff_alloc = allocate(by_speculative, total_combos * skew.bluff_share)

    fully_narrowed: WeightedRange = {}
    for hand_class in included:
        if hand_class in value_alloc:
            fully_narrowed[hand_class] = value_alloc[hand_class]
        elif hand_class in bluff_alloc:
            fully_narrowed[hand_class] = bluff_alloc[hand_class]
        else:
            fully_narrowed[hand_class] = 0.0  # filler -- fully cut at reliability=100

    blend = reliability / 100.0
    result = {
        hand_class: range_in[hand_class] * (1.0 - blend) + fully_narrowed[hand_class] * blend
        for hand_class in included
    }
    result = {c: w for c, w in result.items() if w > 1e-9}
    return FilterResult(result, diff_ranges(range_in, result))


@dataclass(frozen=True)
class RangePredictorInputs:
    position: str
    action: str
    player_type: str
    sizing_bucket: str | None = None
    reliability: int | None = None  # None => use player_type's default


@dataclass(frozen=True)
class RangePredictorStage:
    name: StageName
    range: WeightedRange
    diff: RangeDiff


@dataclass(frozen=True)
class RangePredictorResult:
    final: WeightedRange
    combo_count: float
    stages: list[RangePredictorStage]
    reliability_used: int
    reliability_default: int
    reliability_is_customized: bool


def compute_range(inputs: RangePredictorInputs) -> RangePredictorResult:
    """Runs the Position -> Player Type -> Bet Sizing pipeline. Each stage is
    a pure filter over the previous stage's WeightedRange, recorded with its
    diff so a future layer-stepper/Explain UI can replay construction
    without re-deriving it."""
    baseline = baseline_range(inputs.position, inputs.action)
    stages = [RangePredictorStage("position", baseline, RangeDiff({}, {}, {}))]

    pt_result = apply_player_type(baseline, inputs.player_type)
    stages.append(RangePredictorStage("player_type", pt_result.range, pt_result.diff))

    default_reliability = PLAYER_TYPE_MODIFIERS[inputs.player_type].default_reliability
    reliability = (
        inputs.reliability if inputs.reliability is not None else default_reliability
    )

    bs_result = apply_bet_sizing(
        pt_result.range, inputs.action, inputs.sizing_bucket, reliability
    )
    stages.append(RangePredictorStage("bet_sizing", bs_result.range, bs_result.diff))

    return RangePredictorResult(
        final=bs_result.range,
        combo_count=_weighted_combo_count(bs_result.range),
        stages=stages,
        reliability_used=reliability,
        reliability_default=default_reliability,
        reliability_is_customized=(
            inputs.reliability is not None and inputs.reliability != default_reliability
        ),
    )

"""Bet-sizing value:bluff skew, by (action, sizing_bucket, street). Only
meaningful for actions with a variable raise size (open/threebet/fourbet);
coldcall/limp have no sizing choice and are a documented no-op in
range_predictor.apply_bet_sizing. Keyed by street too (kept for forward-compat
with the deferred multi-street/board-texture factors) but this pass only
populates "preflop".

`value_share` and `bluff_share` are target fractions of the *original*
(pre-bet-sizing) range's weighted combos that survive at full confidence as
value / bluff respectively; the remainder is "filler" (medium-strength hands
that don't fit either story), which is exactly what the reliability slider
softens or hard-cuts in apply_bet_sizing. Bigger sizes are modeled as more
polarized: value_share + bluff_share *shrinks* as size increases, since a
large/overbet size is a much more selective, narrow action than a small one
-- more of the original range gets discarded as filler, not less."""

from dataclasses import dataclass

Street = str  # "preflop" only for this pass; "flop"/"turn"/"river" reserved for later


@dataclass(frozen=True)
class SizingSkew:
    value_share: float  # target fraction of the range's weighted combos that are "value"
    bluff_share: float  # target fraction that are speculative/bluff candidates


BET_SIZING_SKEW: dict[tuple[str, str, Street], SizingSkew] = {
    ("open", "small", "preflop"): SizingSkew(0.65, 0.30),
    ("open", "medium", "preflop"): SizingSkew(0.55, 0.25),
    ("open", "large", "preflop"): SizingSkew(0.45, 0.20),
    ("threebet", "small", "preflop"): SizingSkew(0.70, 0.25),
    ("threebet", "medium", "preflop"): SizingSkew(0.55, 0.20),
    ("threebet", "large", "preflop"): SizingSkew(0.40, 0.15),
    ("fourbet", "small", "preflop"): SizingSkew(0.75, 0.20),
    ("fourbet", "medium", "preflop"): SizingSkew(0.60, 0.15),
    ("fourbet", "large", "preflop"): SizingSkew(0.45, 0.10),
}

NON_SIZING_ACTIONS = frozenset({"coldcall", "limp"})

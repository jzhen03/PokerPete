"""Player-type baseline-shape modifiers -- widen/narrow the position baseline
and bias its linear/polarized ordering. This is independent of bet-sizing
reliability (a separate stage, see bet_sizing_skew.py), though each type's
`default_reliability` seeds that stage's reliability slider."""

from dataclasses import dataclass
from typing import Literal

Shift = Literal["linear", "polarized", "neutral"]


@dataclass(frozen=True)
class PlayerTypeModifier:
    width_delta_pct: float  # e.g. +35 widens weighted combo count 35%, -30 narrows 30%
    shift: Shift  # bias applied when choosing *which* hands to add/drop
    default_reliability: int  # 0-100, seeds the bet-sizing filter's reliability slider


PLAYER_TYPE_MODIFIERS: dict[str, PlayerTypeModifier] = {
    "loose_passive": PlayerTypeModifier(35, "linear", 80),
    "tight_passive": PlayerTypeModifier(-30, "linear", 80),
    "loose_aggressive": PlayerTypeModifier(25, "polarized", 35),
    "tight_aggressive": PlayerTypeModifier(-15, "polarized", 55),
    "balanced": PlayerTypeModifier(0, "neutral", 15),
}

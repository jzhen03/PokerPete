from __future__ import annotations

import json
from pathlib import Path

from pokerpete.engine import equity, ranges

RANKS = "23456789TJQKA"
DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "preflop_equity_matrix.json"


def canonical_hand_classes() -> tuple[str, ...]:
    """All 169 canonical starting-hand notations: 'AA', 'AKs', 'AKo', ..."""
    classes: list[str] = []
    for hi in range(12, -1, -1):
        for lo in range(hi, -1, -1):
            if hi == lo:
                classes.append(RANKS[hi] * 2)
            else:
                classes.append(RANKS[hi] + RANKS[lo] + "s")
                classes.append(RANKS[hi] + RANKS[lo] + "o")
    return tuple(classes)


def class_weight(hand_class: str) -> float:
    """Fraction of all 1326 starting combos this hand class represents."""
    return ranges.combo_count(ranges.parse(hand_class)) / 1326.0


def build_matrix(*, iterations: int = 2000, seed: int = 0) -> dict[str, dict[str, float]]:
    """All-in preflop equity of row hand-class vs. column hand-class.

    `matrix[a][b]` is a's win-equity against b. This is the expensive,
    one-time part of preflop solving (169x169 Monte Carlo range-vs-range
    calls); `preflop_solver.py` only ever consumes the result as a plain
    lookup table, so it can be tested against a small hand-written matrix
    instead of paying this cost. `matrix[b][a] == 1 - matrix[a][b]` by
    symmetry, so only the upper triangle is actually simulated.
    """
    classes = canonical_hand_classes()
    parsed = {c: ranges.parse(c) for c in classes}
    matrix: dict[str, dict[str, float]] = {c: {} for c in classes}

    for i, class_a in enumerate(classes):
        matrix[class_a][class_a] = 0.5  # a class mirrored against itself is symmetric
        for class_b in classes[i + 1 :]:
            result = equity.range_vs_range(
                parsed[class_a], parsed[class_b], iterations=iterations, seed=seed
            )
            matrix[class_a][class_b] = result.equity
            matrix[class_b][class_a] = 1.0 - result.equity
    return matrix


def save_matrix(matrix: dict[str, dict[str, float]], path: Path = DEFAULT_DATA_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(matrix, f, indent=2, sort_keys=True)


def load_matrix(path: Path = DEFAULT_DATA_PATH) -> dict[str, dict[str, float]]:
    with path.open() as f:
        return json.load(f)

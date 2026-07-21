#!/usr/bin/env python
"""Offline batch job: builds the 169x169 canonical preflop equity matrix and
writes it to engine/data/preflop_equity_matrix.json. Takes several minutes;
re-run only if the underlying equity engine's methodology changes.
"""

from __future__ import annotations

import time

from pokerpete.engine.preflop_equity_matrix import build_matrix, save_matrix


def main() -> None:
    start = time.monotonic()
    matrix = build_matrix()
    save_matrix(matrix)
    print(f"Built 169x169 preflop equity matrix in {time.monotonic() - start:.1f}s")


if __name__ == "__main__":
    main()

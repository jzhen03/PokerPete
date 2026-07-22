"""DB-backed cache for expensive preflop tree solves. Keeps
engine/preflop_tree_solver.py framework-free -- this is the only place that
knows about both the solver and the database."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from pokerpete.db.models import SolverResult
from pokerpete.engine.preflop_equity_matrix import default_matrix, default_weights
from pokerpete.engine.preflop_tree_solver import (
    OPEN_SIZE_BB,
    SOLVER_VERSION,
    TreeSolution,
    solve_open_tree,
)

DEFAULT_ITERATIONS = 300


def _cache_key(solver_version: str, params: dict[str, float]) -> str:
    raw = solver_version + json.dumps(params, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def get_or_solve_tree(
    db: Session, stack_bb: float, *, iterations: int = DEFAULT_ITERATIONS
) -> TreeSolution:
    params = {"stack_bb": stack_bb, "open_size_bb": OPEN_SIZE_BB, "iterations": iterations}
    cache_key = _cache_key(SOLVER_VERSION, params)

    cached = db.scalar(select(SolverResult).where(SolverResult.cache_key == cache_key))
    if cached is not None:
        return TreeSolution(**json.loads(cached.result_json))

    solution = solve_open_tree(
        default_matrix(),
        stack_bb,
        weights=default_weights(),
        open_size_bb=OPEN_SIZE_BB,
        iterations=iterations,
    )
    db.add(
        SolverResult(
            cache_key=cache_key,
            solver_version=SOLVER_VERSION,
            tree_params_json=json.dumps(params, sort_keys=True),
            result_json=json.dumps(asdict(solution)),
            computed_at=datetime.now(UTC),
        )
    )
    db.commit()
    return solution

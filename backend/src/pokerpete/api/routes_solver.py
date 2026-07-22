from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from pokerpete.db.session import get_db
from pokerpete.db.solver_cache import get_or_solve_tree
from pokerpete.engine.preflop_solver import solve_push_fold_cached
from pokerpete.engine.preflop_tree_solver import MODEL_CAVEAT
from pokerpete.schemas.solver import (
    PreflopTreeRequest,
    PreflopTreeResponse,
    PushFoldRequest,
    PushFoldResponse,
)

router = APIRouter(prefix="/solver", tags=["solver"])


@router.post("/push-fold", response_model=PushFoldResponse)
def solve_push_fold_route(request: PushFoldRequest) -> PushFoldResponse:
    solution = solve_push_fold_cached(request.stack_bb)
    return PushFoldResponse(
        stack_bb=solution.stack_bb,
        iterations=solution.iterations,
        sb_shove_frequency=dict(solution.sb_shove_frequency),
        bb_call_frequency=dict(solution.bb_call_frequency),
    )


@router.post("/preflop-tree", response_model=PreflopTreeResponse)
def solve_preflop_tree_route(
    request: PreflopTreeRequest, db: Session = Depends(get_db)
) -> PreflopTreeResponse:
    solution = get_or_solve_tree(db, request.stack_bb)
    return PreflopTreeResponse(
        stack_bb=solution.stack_bb,
        open_size_bb=solution.open_size_bb,
        threebet_size_bb=solution.threebet_size_bb,
        iterations=solution.iterations,
        sb_root={k: dict(v) for k, v in solution.sb_root.items()},
        bb_vs_open={k: dict(v) for k, v in solution.bb_vs_open.items()},
        sb_vs_3bet={k: dict(v) for k, v in solution.sb_vs_3bet.items()},
        bb_vs_shove={k: dict(v) for k, v in solution.bb_vs_shove.items()},
        sb_vs_shove_after_open={k: dict(v) for k, v in solution.sb_vs_shove_after_open.items()},
        bb_vs_shove_after_3bet={k: dict(v) for k, v in solution.bb_vs_shove_after_3bet.items()},
        caveat=MODEL_CAVEAT,
    )

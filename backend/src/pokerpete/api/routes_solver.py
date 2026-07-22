from fastapi import APIRouter

from pokerpete.engine.preflop_solver import solve_push_fold_cached
from pokerpete.schemas.solver import PushFoldRequest, PushFoldResponse

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

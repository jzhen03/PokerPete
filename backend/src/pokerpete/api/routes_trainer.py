from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from pokerpete.db.session import get_db
from pokerpete.db.solver_cache import get_or_solve_tree
from pokerpete.engine.preflop_equity_matrix import canonical_hand_classes
from pokerpete.engine.preflop_tree_solver import MODEL_CAVEAT
from pokerpete.engine.trainer import grade_push_fold, random_push_fold_spot, random_tree_spot
from pokerpete.schemas.trainer import (
    PushFoldGradeRequest,
    PushFoldGradeResponse,
    PushFoldSpotResponse,
    TreeGradeRequest,
    TreeGradeResponse,
    TreeSpotResponse,
)

router = APIRouter(prefix="/trainer", tags=["trainer"])

_VALID_CLASSES = frozenset(canonical_hand_classes())


@router.get("/push-fold/spot", response_model=PushFoldSpotResponse)
def get_spot() -> PushFoldSpotResponse:
    spot = random_push_fold_spot()
    return PushFoldSpotResponse(
        stack_bb=spot.stack_bb, hero_class=spot.hero_class, hero_combo=spot.hero_combo
    )


@router.post("/push-fold/grade", response_model=PushFoldGradeResponse)
def grade_spot(request: PushFoldGradeRequest) -> PushFoldGradeResponse:
    if request.hero_class not in _VALID_CLASSES:
        raise HTTPException(status_code=422, detail=f"unknown hand class: {request.hero_class!r}")

    grade = grade_push_fold(request.stack_bb, request.hero_class, request.action)
    return PushFoldGradeResponse(
        correct=grade.correct,
        correct_action=grade.correct_action,
        shove_frequency=grade.shove_frequency,
    )


@router.get("/preflop-tree/spot", response_model=TreeSpotResponse)
def get_tree_spot() -> TreeSpotResponse:
    spot = random_tree_spot()
    return TreeSpotResponse(
        stack_bb=spot.stack_bb, hero_class=spot.hero_class, hero_combo=spot.hero_combo
    )


@router.post("/preflop-tree/grade", response_model=TreeGradeResponse)
def grade_tree_spot(
    request: TreeGradeRequest, db: Session = Depends(get_db)
) -> TreeGradeResponse:
    if request.hero_class not in _VALID_CLASSES:
        raise HTTPException(status_code=422, detail=f"unknown hand class: {request.hero_class!r}")

    solution = get_or_solve_tree(db, request.stack_bb)
    frequencies = solution.sb_root[request.hero_class]
    correct_action = max(frequencies, key=lambda a: frequencies[a])
    return TreeGradeResponse(
        correct=request.action == correct_action,
        correct_action=correct_action,
        action_frequencies=dict(frequencies),
        caveat=MODEL_CAVEAT,
    )

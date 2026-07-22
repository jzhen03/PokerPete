from fastapi import APIRouter, HTTPException

from pokerpete.engine.preflop_equity_matrix import canonical_hand_classes
from pokerpete.engine.trainer import grade_push_fold, random_push_fold_spot
from pokerpete.schemas.trainer import (
    PushFoldGradeRequest,
    PushFoldGradeResponse,
    PushFoldSpotResponse,
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

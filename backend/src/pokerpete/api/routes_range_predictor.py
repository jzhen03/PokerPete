from fastapi import APIRouter

from pokerpete.engine.range_predictor import RangePredictorInputs, compute_range
from pokerpete.schemas.range_predictor import (
    RangePredictRequest,
    RangePredictResponse,
    RangeStage,
)

router = APIRouter(prefix="/ranges", tags=["ranges"])


@router.post("/predict", response_model=RangePredictResponse)
def predict_range(request: RangePredictRequest) -> RangePredictResponse:
    inputs = RangePredictorInputs(
        position=request.position,
        action=request.action,
        player_type=request.player_type,
        sizing_bucket=request.sizing_bucket,
        reliability=request.reliability,
    )
    result = compute_range(inputs)
    return RangePredictResponse(
        classes=result.final,
        combo_count=result.combo_count,
        stages=[
            RangeStage(
                name=stage.name,
                classes=stage.range,
                added=stage.diff.added,
                removed=stage.diff.removed,
                reweighted=stage.diff.reweighted,
            )
            for stage in result.stages
        ],
        reliability_used=result.reliability_used,
        reliability_default=result.reliability_default,
        reliability_is_customized=result.reliability_is_customized,
    )

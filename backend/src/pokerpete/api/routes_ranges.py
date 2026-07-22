from fastapi import APIRouter, HTTPException

from pokerpete.engine import ranges
from pokerpete.schemas.ranges import RangeParseRequest, RangeParseResponse

router = APIRouter(prefix="/ranges", tags=["ranges"])


@router.post("/parse", response_model=RangeParseResponse)
def parse_range(request: RangeParseRequest) -> RangeParseResponse:
    try:
        parsed = ranges.parse(request.notation)
    except Exception as exc:
        # eval7's range-notation grammar raises its own parser-specific
        # exception types, which aren't part of our stable contract -- any
        # failure to parse user-supplied notation is a 422 at this boundary.
        raise HTTPException(status_code=422, detail=f"invalid range notation: {exc}") from exc

    return RangeParseResponse(
        classes=ranges.class_weights(parsed),
        combo_count=ranges.combo_count(parsed),
    )

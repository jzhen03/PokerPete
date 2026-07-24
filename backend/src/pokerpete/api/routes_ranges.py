import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from pokerpete.db.saved_ranges import create_saved_range, get_saved_range, list_saved_ranges
from pokerpete.db.session import get_db
from pokerpete.engine import ranges
from pokerpete.schemas.ranges import (
    RangeParseRequest,
    RangeParseResponse,
    SavedRangeCreate,
    SavedRangeDetail,
    SavedRangeSummary,
)

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


def _weighted_combo_count(classes: dict[str, float]) -> float:
    return sum(w * ranges.combo_count(ranges.parse(c)) for c, w in classes.items() if w > 0)


@router.post("", response_model=SavedRangeSummary, status_code=201)
def save_range(request: SavedRangeCreate, db: Session = Depends(get_db)) -> SavedRangeSummary:
    row = create_saved_range(
        db,
        name=request.name,
        source=request.source,
        classes=request.classes,
        notation=request.notation,
        position=request.position,
        tags=request.tags,
        factors=request.factors,
    )
    return SavedRangeSummary(
        id=row.id,
        name=row.name,
        source=row.source,
        position=row.position,
        created_at=row.created_at,
    )


@router.get("", response_model=list[SavedRangeSummary])
def list_ranges(db: Session = Depends(get_db)) -> list[SavedRangeSummary]:
    return [
        SavedRangeSummary(
            id=row.id, name=row.name, source=row.source, position=row.position,
            created_at=row.created_at,
        )
        for row in list_saved_ranges(db)
    ]


@router.get("/{range_id}", response_model=SavedRangeDetail)
def get_range(range_id: int, db: Session = Depends(get_db)) -> SavedRangeDetail:
    row = get_saved_range(db, range_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no saved range with id {range_id}")

    classes = json.loads(row.classes_json)
    return SavedRangeDetail(
        id=row.id,
        name=row.name,
        source=row.source,
        position=row.position,
        created_at=row.created_at,
        classes=classes,
        combo_count=_weighted_combo_count(classes),
        notation=row.notation,
        factors=json.loads(row.factors_json) if row.factors_json else None,
    )

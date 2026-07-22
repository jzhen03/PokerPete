from fastapi import APIRouter, HTTPException

from pokerpete.engine import cards, equity, ranges
from pokerpete.schemas.equity import EquityRequest, EquityResponse

router = APIRouter(prefix="/equity", tags=["equity"])


@router.post("/calculate", response_model=EquityResponse)
def calculate_equity(request: EquityRequest) -> EquityResponse:
    try:
        hero_range = ranges.parse(request.hero)
        villain_range = ranges.parse(request.villain)
        board = cards.parse_cards(request.board) if request.board else ()
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"invalid hand/board: {exc}") from exc

    try:
        # A single-combo range on both sides is a specific hand-vs-hand
        # matchup, which gets exact enumeration on the turn/river instead of
        # Monte Carlo -- worth the branch for the common "check this one
        # hand" case.
        if len(hero_range) == 1 and len(villain_range) == 1:
            (hero_combo,) = hero_range.keys()
            (villain_combo,) = villain_range.keys()
            result = equity.hand_vs_hand(
                tuple(hero_combo), tuple(villain_combo), board, iterations=request.iterations
            )
        else:
            result = equity.range_vs_range(
                hero_range, villain_range, board, iterations=request.iterations
            )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return EquityResponse(win=result.win, tie=result.tie, lose=result.lose, equity=result.equity)

from typing import Literal

from pydantic import BaseModel, Field

Position = Literal["SB", "BB"]
Action = Literal["open", "threebet", "fourbet", "coldcall", "limp"]
PlayerType = Literal[
    "loose_passive", "tight_passive", "loose_aggressive", "tight_aggressive", "balanced"
]
SizingBucket = Literal["small", "medium", "large"]


class RangePredictRequest(BaseModel):
    position: Position
    action: Action
    player_type: PlayerType
    sizing_bucket: SizingBucket | None = None
    reliability: int | None = Field(default=None, ge=0, le=100)


class RangeStage(BaseModel):
    name: str
    classes: dict[str, float]
    added: dict[str, float]
    removed: dict[str, float]
    reweighted: dict[str, tuple[float, float]]


class RangePredictResponse(BaseModel):
    classes: dict[str, float]
    combo_count: float
    stages: list[RangeStage]
    reliability_used: int
    reliability_default: int
    reliability_is_customized: bool

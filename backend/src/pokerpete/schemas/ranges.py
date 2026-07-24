from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class RangeParseRequest(BaseModel):
    notation: str


class RangeParseResponse(BaseModel):
    classes: dict[str, float]
    combo_count: float


class SavedRangeCreate(BaseModel):
    name: str
    source: Literal["predictor", "notation"] = "predictor"
    classes: dict[str, float]
    notation: str | None = None
    position: str | None = None
    tags: list[str] | None = None
    factors: dict | None = None


class SavedRangeSummary(BaseModel):
    id: int
    name: str
    source: str
    position: str | None
    created_at: datetime


class SavedRangeDetail(SavedRangeSummary):
    classes: dict[str, float]
    combo_count: float
    notation: str | None
    factors: dict | None

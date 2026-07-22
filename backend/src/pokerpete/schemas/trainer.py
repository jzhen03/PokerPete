from typing import Literal

from pydantic import BaseModel, Field


class PushFoldSpotResponse(BaseModel):
    stack_bb: float
    hero_class: str
    hero_combo: str


class PushFoldGradeRequest(BaseModel):
    stack_bb: float = Field(gt=0)
    hero_class: str
    action: Literal["shove", "fold"]


class PushFoldGradeResponse(BaseModel):
    correct: bool
    correct_action: Literal["shove", "fold"]
    shove_frequency: float


class TreeSpotResponse(BaseModel):
    stack_bb: float
    hero_class: str
    hero_combo: str


class TreeGradeRequest(BaseModel):
    stack_bb: float = Field(gt=0)
    hero_class: str
    action: Literal["fold", "open", "shove"]


class TreeGradeResponse(BaseModel):
    correct: bool
    correct_action: Literal["fold", "open", "shove"]
    action_frequencies: dict[str, float]
    caveat: str

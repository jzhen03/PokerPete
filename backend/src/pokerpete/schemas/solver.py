from pydantic import BaseModel, Field


class PushFoldRequest(BaseModel):
    stack_bb: float = Field(gt=0)


class PushFoldResponse(BaseModel):
    stack_bb: float
    iterations: int
    sb_shove_frequency: dict[str, float]
    bb_call_frequency: dict[str, float]

from pydantic import BaseModel, Field


class PushFoldRequest(BaseModel):
    stack_bb: float = Field(gt=0)


class PushFoldResponse(BaseModel):
    stack_bb: float
    iterations: int
    sb_shove_frequency: dict[str, float]
    bb_call_frequency: dict[str, float]


class PreflopTreeRequest(BaseModel):
    stack_bb: float = Field(gt=0)


class PreflopTreeResponse(BaseModel):
    stack_bb: float
    open_size_bb: float
    threebet_size_bb: float
    iterations: int
    sb_root: dict[str, dict[str, float]]
    bb_vs_open: dict[str, dict[str, float]]
    sb_vs_3bet: dict[str, dict[str, float]]
    bb_vs_shove: dict[str, dict[str, float]]
    sb_vs_shove_after_open: dict[str, dict[str, float]]
    bb_vs_shove_after_3bet: dict[str, dict[str, float]]
    caveat: str

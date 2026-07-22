from pydantic import BaseModel, Field


class EquityRequest(BaseModel):
    hero: str
    villain: str
    board: str = ""
    iterations: int = Field(default=5000, gt=0)


class EquityResponse(BaseModel):
    win: float
    tie: float
    lose: float
    equity: float

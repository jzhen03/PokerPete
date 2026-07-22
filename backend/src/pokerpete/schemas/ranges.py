from pydantic import BaseModel


class RangeParseRequest(BaseModel):
    notation: str


class RangeParseResponse(BaseModel):
    classes: dict[str, float]
    combo_count: float

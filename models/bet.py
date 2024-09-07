from typing import Literal

from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class BetCreate(BaseSchema):
    event_request_id: str
    wallet_address: str
    prediction: Literal["YES", "NO"]
    tokens: float = Field(gt=0)


class BetResponse(BetCreate):
    id: int

    class Config:
        from_attributes = True

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class PredictInfo(BaseModel):
    price: str
    symbol: str


class EventCreate(BaseSchema):
    request_id: str
    title: str
    description: str
    due_date: int
    predict: PredictInfo | None = None


class ContractsUpdate(BaseSchema):
    contracts: dict[str, str]


class EventResponse(BaseSchema):
    request_id: str
    title: str
    description: str
    due_date: int
    predict: PredictInfo | None = None
    contracts: dict[str, str] | None = None

    class Config:
        from_attributes = True

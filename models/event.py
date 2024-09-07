from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class EventCreate(BaseSchema):
    smart_contract_address: str
    network: str
    title: str
    description: str


class EventResponse(EventCreate):
    id: int

    class Config:
        from_attributes = True

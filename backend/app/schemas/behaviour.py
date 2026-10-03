from pydantic import (
    BaseModel,
    ConfigDict
)

# Esta implementado la iss-72 y 74 donde se pide la lista de comportamientos y el detalle de un comportamiento

class BehaviourRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str


class BehaviourListResponse(BaseModel):
    items: list[BehaviourRead]


class BehaviourReadDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
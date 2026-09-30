from pydantic import (
    BaseModel,
    ConfigDict
)

class BehaviourRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    
class BehaviourListResponse(BaseModel):
    items: list[BehaviourRead]
from pydantic import BaseModel, ConfigDict, Field

#Esto es para que React sepa que leer
class DtBehaviourRead(BaseModel):
    model_config = ConfigDict(from_attributes = True)
    id: int
    name: str
    code: str

#Pero esto es cuando se crea un behaviour y viene desde el front
class DtBehaviourCreate(BaseModel):
    name: str = Field(min_length = 1, max_length = 30)
    code: str 


class DtRead(BaseModel):
    model_config = ConfigDict(from_attributes = True)

    id: int
    is_active: bool = Field(serialization_alias = "isActive")
    active_behaviour_id: int | None = Field(serialization_alias = "activeBehaviourId")


class DtUpdate(BaseModel):
    is_active: bool = Field(alias = "isActive")
    active_behaviour_id: int | None = Field(alias = "activeBehaviourId", default = None)

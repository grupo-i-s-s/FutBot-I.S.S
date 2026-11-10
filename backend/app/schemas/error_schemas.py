from pydantic import BaseModel

from app.schemas.behaviour_schemas import BehaviourDiagnostic


class ApiErrorDetail(BaseModel):
    code: str
    message: str
    fields: dict[str, str]
    diagnostics: list[BehaviourDiagnostic] | None = None


class ApiErrorResponse(BaseModel):
    error: ApiErrorDetail


class HttpErrorResponse(BaseModel):
    detail: str

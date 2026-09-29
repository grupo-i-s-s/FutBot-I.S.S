from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator, model_validator

Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
]

NewPassword = Annotated[
    str,
    Field(min_length=8, max_length=128)
]


class InputSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(InputSchema):
    name: Name

    username: str = Field(
        min_length=3,
        max_length=30,
        pattern=r"^[a-z0-9_]+$",
    )

    email: EmailStr = Field(max_length=254)

    password: NewPassword

    password_confirmation: str = Field(alias="passwordConfirmation", max_length=128)

    club_name: Name = Field(alias="clubName")

    avatar: str = Field(min_length=1, max_length=100)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()

    @model_validator(mode="after")
    def validate_password_confirmation(self):
        if self.password != self.password_confirmation:
            raise ValueError("Las contraseñas no coinciden")
        return self


class LoginRequest(InputSchema):
    email: EmailStr = Field(max_length=254)

    password: str = Field(
        min_length=1,
        max_length=128,
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class ChangePasswordRequest(InputSchema):
    old_password: str = Field(
        alias="oldPassword",
        min_length=1,
        max_length=128,
    )

    new_password: NewPassword = Field(
        alias="newPassword",
    )


class UserResponse(BaseModel):
    id: int
    name: str
    username: str
    email: str

    club_id: int = Field(
        serialization_alias="clubId",
    )

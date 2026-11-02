from typing import Annotated

from pydantic import StringConstraints


DEFAULT_AVATAR = "avatar-01.png"

AvatarFilename = Annotated[
    str,
    StringConstraints(
        pattern=r"^avatar-(0[1-9]|1[0-9]|20)\.png$",
    ),
]
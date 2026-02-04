import abc
from typing import Annotated

from pydantic import BaseModel, StringConstraints
from pydantic.dataclasses import dataclass
from brilliance_admin.utils import DataclassBase

Username = Annotated[str, StringConstraints(pattern=r'^[a-zA-Z0-9@._-]{1,150}$')]


@dataclass
class UserABC(DataclassBase, abc.ABC):
    username: str


class AuthData(BaseModel):
    username: Username
    password: str


class UserResult(BaseModel):
    username: str


class AuthResult(BaseModel):
    token: str
    user: UserResult


class AdminAuthentication(abc.ABC):
    async def login(self, data: AuthData, debug: bool = False) -> AuthResult:
        raise NotImplementedError('Login is not implemented')

    async def authenticate(self, headers: dict) -> UserABC:
        raise NotImplementedError('authenticate is not implemented')

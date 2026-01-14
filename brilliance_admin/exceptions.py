from typing import Dict

from pydantic import Field
from pydantic.dataclasses import dataclass

from brilliance_admin.utils import DataclassBase, SupportsStr


@dataclass
class FieldError(DataclassBase, Exception):
    message: SupportsStr = None
    code: str | None = None
    field_slug: str | None = None

    def __post_init__(self):
        if not self.message and not self.code:
            msg = 'FieldError must contain message or code'
            raise AttributeError(msg)


@dataclass
class APIError(DataclassBase):
    message: SupportsStr | None = None
    code: str | None = None
    field_errors: Dict[str, FieldError] | None = None


@dataclass
class AdminAPIException(DataclassBase, Exception):
    error: APIError = Field(default_factory=APIError)
    status_code: int = 400
    error_code: str | None = None

    def __str__(self):
        return str(self.error)

    def get_error(self) -> APIError:
        return self.error

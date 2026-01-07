from typing import Any, Dict, List

from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass

from brilliance_admin.utils import DataclassBase


@dataclass
class TableListResult(DataclassBase):
    data: List[dict]
    total_count: int


class AutocompleteData(BaseModel):
    field_slug: str
    search_string: str = ''
    is_filter: bool = False
    form_data: dict = Field(default_factory=dict)
    existed_choices: List[Any] = Field(default_factory=list)
    action_name: str | None = None
    limit: int = 25


class Record(BaseModel):
    key: Any
    title: str


class AutocompleteResult(BaseModel):
    results: List[Record] = Field(default_factory=list)


class ListData(BaseModel):
    page: int = 1
    limit: int = 25

    search: str | None = None
    filters: Dict[str, Any] = Field(default_factory=dict)

    ordering: str | None = None


class RetrieveResult(BaseModel):
    data: dict


class CreateResult(BaseModel):
    pk: Any


class UpdateResult(BaseModel):
    pk: Any

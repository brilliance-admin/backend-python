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
    form_data: dict = Field(default_factory=dict)
    existed_choices: List[Any] = Field(default_factory=list)
    limit: int = Field(default=25, le=250)

    # Type of autocomplete:
    is_filter: bool = False
    action_name: str | None = None
    inline_field_slug: str | None = None


class Record(BaseModel):
    key: Any
    title: str


class AutocompleteResult(BaseModel):
    results: List[Record] = Field(default_factory=list)


class ListData(BaseModel):
    page: int = 1
    limit: int = Field(default=25, le=250)

    search: str | None = None
    filters: Dict[str, Any] = Field(default_factory=dict)

    ordering: str | None = None


class RetrieveResult(BaseModel):
    data: dict


class CreateResult(BaseModel):
    pk: Any


class UpdateResult(BaseModel):
    pk: Any

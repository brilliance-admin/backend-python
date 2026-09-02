from dataclasses import field
from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator
from pydantic.dataclasses import dataclass

from brilliance_admin.utils import DataclassBase


@dataclass
class DebugQuery(DataclassBase):
    sql: str
    time_ms: float | None = None


@dataclass
class DebugInfo(DataclassBase):
    db_query_count: int
    queries: List[DebugQuery]
    serialize_ms: float | None = None


@dataclass
class TableListResult(DataclassBase):
    data: List[dict]
    total_count: str | None
    pages_count: int | None = field(default=None, compare=False)
    debug_info: DebugInfo | None = None

    @field_validator('total_count', mode='before')
    @classmethod
    def serialize_total_count(cls, value):
        if value is None or isinstance(value, str):
            return value
        return str(value)


class AutocompleteData(BaseModel):
    field_slug: str = ''
    search_string: str = ''
    form_data: dict = Field(default_factory=dict)
    existed_choices: List[Any] = Field(default_factory=list)
    limit: int = Field(default=25, le=250)

    # Type of autocomplete:
    is_filter: bool = False
    action_name: str | None = None
    inline_field_slug: str | None = None
    parent_pk: Any | None = None


class Record(BaseModel):
    key: Any
    title: str


class AutocompleteResult(BaseModel):
    results: List[Record] = Field(default_factory=list)
    total_count: int


class ListData(BaseModel):
    page: int = 1
    limit: int = Field(default=25, le=250)

    search: str | None = None
    filters: Dict[str, Any] = Field(default_factory=dict)

    ordering: str | None = None
    parent_pk: Any | None = None


class RetrieveResult(BaseModel):
    data: dict
    debug_info: DebugInfo | None = None


class CreateResult(BaseModel):
    pk: Any
    choice: Record | None = None
    debug_info: DebugInfo | None = None


class UpdateResult(BaseModel):
    pk: Any
    debug_info: DebugInfo | None = None

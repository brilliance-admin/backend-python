from dataclasses import field
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator
from pydantic.dataclasses import dataclass

from brilliance_admin.schema.chart import ChartData
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
    # The view receives field_slug as a query parameter and assigns it after body validation.
    field_slug: str | None = None

    # If search presents must filter output records
    # If empty - all records limited with "limit" count must returned
    search_string: str | None = None

    form_data: dict = Field(default_factory=dict)

    # Adding exiting options to the output for the titles
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
    records: List[Record] = Field(default_factory=list)
    current_count: int = 0
    total_count: str | None = None


class FilterSubtableUnitSize(str, Enum):
    TEN_MINUTES = '10min'
    HOUR = '1hour'
    DAY = '1day'


class FilterSubtableData(BaseModel):
    field_slug: str = ''
    unit_size: FilterSubtableUnitSize
    filters: Dict[str, Any] = Field(default_factory=dict)
    search: str | None = None


class FilterSubtableResult(BaseModel):
    chart: ChartData


class ListData(BaseModel):
    page: int = 1
    limit: int = Field(default=25, le=250)

    search: str | None = None
    filters: Dict[str, Any] = Field(default_factory=dict)

    ordering: str | None = None
    parent_pk: Any | None = None


class RetrieveResult(BaseModel):
    data: dict
    tab_counts: Dict[str, str | None] = Field(default_factory=dict)
    debug_info: DebugInfo | None = None


class CreateResult(BaseModel):
    pk: Any
    choice: Record | None = None
    debug_info: DebugInfo | None = None


class UpdateResult(BaseModel):
    pk: Any
    debug_info: DebugInfo | None = None

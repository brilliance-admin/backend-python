from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_serializer

from brilliance_admin.schema.category import BaseCategory, DashboardInfoSchemaData
from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import SupportsStr


class DashboardData(BaseModel):
    search: str | None = None
    filters: Dict[str, Any] = Field(default_factory=dict)


class ChartData(BaseModel):
    data: dict
    options: dict
    width: int | None = None
    height: int = 50
    type: str = 'line'

    component_type: str = 'chart'


class Subcard(BaseModel):
    title: SupportsStr
    value: SupportsStr
    color: str | None = None


class PeriodGraph(BaseModel):
    title: SupportsStr
    value: SupportsStr
    change: int | float | None = None
    subcards: List[Subcard] = Field(default_factory=list)
    values: List[List[int | float]] = Field(default_factory=list)
    vertical: List[SupportsStr] = Field(default_factory=list)
    horizontal: List[SupportsStr] = Field(default_factory=list)
    component_type: str = 'period_graph'

    @field_serializer('horizontal', 'vertical')
    def serialize_str_list(self, val: list) -> list:
        return [str(v) for v in val]


class SmallGraph(BaseModel):
    title: SupportsStr
    value: SupportsStr
    change: int | float | None = None
    points: Dict[SupportsStr, float | int] = Field(default_factory=list)
    component_type: str = 'small_graph'


class DashboardContainer(BaseModel):
    cols: int | None = None
    md: int | None = None
    lg: int | None = None
    sm: int | None = None

    component_type: str = 'container'
    components: List[Any] = Field(default_factory=list)


class CategoryDashboard(BaseCategory):
    _type_slug: str = 'dashboard'

    search_enabled: bool = False
    search_help: SupportsStr | None = None

    table_filters: FieldsSchema | None = None

    def generate_schema(self, user, language_context: LanguageContext) -> DashboardInfoSchemaData:
        schema = super().generate_schema(user, language_context)
        dashboard_info = DashboardInfoSchemaData(
            search_enabled=self.search_enabled,
            search_help=language_context.get_text(self.search_help),
        )

        if self.table_filters:
            dashboard_info.table_filters = self.table_filters.generate_schema(user, language_context)

        schema.dashboard_info = dashboard_info
        return schema

    async def get_data(self, data: DashboardData, user) -> DashboardContainer:
        raise NotImplementedError('get_data is not implemented')

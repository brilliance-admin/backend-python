from typing import Any, Dict, List

from pydantic import BaseModel, Field

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


class DashboardDataResult(BaseModel):
    components: List[ChartData] = Field(default_factory=list)


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

    async def get_data(self, data: DashboardData, user) -> DashboardDataResult:
        raise NotImplementedError('get_data is not implemented')

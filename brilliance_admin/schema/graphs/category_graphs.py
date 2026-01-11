from typing import Any, Dict, List

from pydantic import BaseModel, Field

from brilliance_admin.schema.category import BaseCategory, GraphInfoSchemaData
from brilliance_admin.schema.table.fields_schema import FieldsSchema
from brilliance_admin.translations import LanguageContext
from brilliance_admin.utils import SupportsStr


class GraphData(BaseModel):
    search: str | None = None
    filters: Dict[str, Any] = Field(default_factory=dict)


class ChartData(BaseModel):
    data: dict
    options: dict
    width: int | None = None
    height: int = 50
    type: str = 'line'


class GraphsDataResult(BaseModel):
    charts: List[ChartData]


class CategoryGraphs(BaseCategory):
    _type_slug: str = 'graphs'

    search_enabled: bool = False
    search_help: SupportsStr | None = None

    table_filters: FieldsSchema | None = None

    def generate_schema(self, user, language_context: LanguageContext) -> GraphInfoSchemaData:
        schema = super().generate_schema(user, language_context)
        graph = GraphInfoSchemaData(
            search_enabled=self.search_enabled,
            search_help=language_context.get_text(self.search_help),
        )

        if self.table_filters:
            graph.table_filters = self.table_filters.generate_schema(user, language_context)

        schema.graph_info = graph
        return schema

    async def get_data(self, data: GraphData, user) -> GraphsDataResult:
        raise NotImplementedError('get_data is not implemented')

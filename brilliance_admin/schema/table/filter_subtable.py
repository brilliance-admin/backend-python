import abc
from typing import Any

from brilliance_admin.schema.chart import ChartData
from brilliance_admin.schema.table.table_models import FilterSubtableData


class FilterSubtable(abc.ABC):
    @abc.abstractmethod
    async def get_filter_subtable(
            self,
            subtable_data: FilterSubtableData,
            *,
            view: Any,
    ) -> ChartData:
        raise NotImplementedError

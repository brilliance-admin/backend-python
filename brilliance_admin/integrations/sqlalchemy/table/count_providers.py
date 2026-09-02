from brilliance_admin.schema.table.count_providers import CountProvider, CountResult
from brilliance_admin.schema.table.table_models import ListData


class SQLAlchemyCountProvider(CountProvider):
    def __init__(self, db_async_session):
        self.db_async_session = db_async_session

    async def get_count(self, stmt, list_data: ListData) -> CountResult:
        from sqlalchemy import func, select

        count_stmt = select(func.count()).select_from(stmt.subquery())
        async with self.db_async_session() as session:
            count = await session.scalar(count_stmt)
            return CountResult(
                total_count=str(count),
                pages_count=CountResult.get_pages_count(count, list_data.limit),
            )
